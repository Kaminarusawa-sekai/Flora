import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from thespian.actors import Actor, ActorAddress, ActorExitRequest,ChildActorExited
import uuid
from capability_actors.mcp_actor import MCPCapabilityActor
from common.messages.agent_messages import (
    AgentTaskMessage, ResumeTaskMessage, 
)
from common.messages.types import MessageType
from common.messages.task_messages import TaskCompletedMessage
from common.messages.interact_messages import TaskResultMessage, TaskPausedMessage as InteractTaskPausedMessage

# 导入新的能力管理模块
from capabilities import init_capabilities, get_capability, get_capability_registry

# 导入能力接口
from capabilities.llm.interface import ILLMCapability
from capabilities.llm_memory.interface import IMemoryCapability

from capabilities.task_operation.interface import  ITaskOperationCapability

# 导入类型定义
from common.types.draft import TaskDraft
from common.types.intent import IntentResult, IntentType
from common.types.task import Task, TaskType, TaskStatus
from common.types.task_operation import TaskOperationType, TaskOperationCategory

# 导入新的能力接口
from capabilities.intent_router.common_intent_router import IIntentRouterCapability
from capabilities.conversation.interface import IConversationManagerCapability
from capabilities.task_planning.interface import ITaskPlanningCapability

# 导入循环调度器
from capability_actors.loop_scheduler_actor import LoopSchedulerActor


import logging
logger = logging.getLogger(__name__)


# 导入事件总线
from events.event_bus import event_bus
from events.event_types import EventType


##后台

class AgentActor(Actor):
    def __init__(self):
        super().__init__()
        self.agent_id: str = ""
        self.memory_cap: Optional[IMemoryCapability] = None
        self.meta=None

        self._aggregation_state: Dict[str, Dict] = {}
        self.task_id_to_sender: Dict[str, ActorAddress] = {}
        # 新增：保存task_id到ExecutionActor地址的映射（用于恢复暂停的任务）
        self.task_id_to_execution_actor: Dict[str, ActorAddress] = {}
        self.log = logging.getLogger("AgentActor")  # 初始日志，后续按 agent_id 覆盖


        # 添加当前用户ID（实际应从消息中获取）
        self.current_user_id: Optional[str] = None


        # 添加当前聚合器和原始客户端地址
        self.current_aggregator = None
        self.original_client_addr = None
        
        self._task_path: Optional[str] = None

        self.memory_cap: Optional[IMemoryCapability] = None
        self.task_planner: Optional[ITaskPlanningCapability] = None




    def receiveMessage(self, message: Any, sender: ActorAddress):

        if isinstance(message, ActorExitRequest):
            # 可选：做清理工作
            logger.info("Received ActorExitRequest, shutting down.")
            return  # Thespian will destroy the actor automatically
        elif isinstance(message, ChildActorExited):
            # 可选：处理子 Actor 退出
            logger.info(f"Child actor exited: {message.childAddress}, reason: {message.__dict__}")
            return
        try:
            if isinstance(message, AgentTaskMessage):
                # 检查是否需要初始化，如果未初始化则先执行初始化
                if not self.agent_id:
                    # 从AgentTaskMessage中提取agent_id进行初始化
                    self._handle_init_from_task(message, sender)
                self._handle_task(message, sender)
            elif isinstance(message, ResumeTaskMessage):
                self._handle_resume_task(message, sender)
            elif hasattr(message, "message_type") and message.message_type in [MessageType.TASK_PAUSED, "task_paused"]:
                self._handle_task_paused_from_execution(message, sender)
            elif isinstance(message, TaskCompletedMessage):
                self._handle_task_result(message, sender)
            else:
                self.log.warning(f"Unknown message type: {type(message)}")
        except Exception as e:
            self.log.exception(f"Error in AgentActor {self.agent_id}: {e}")

    def _handle_init_from_task(self, msg: AgentTaskMessage, sender: ActorAddress):
        # 从message或context中获取agent_id，这里假设agent_id可以从其他地方获取
        # 或者我们可以从message的task_id中提取，或者使用默认值
        # 这里使用一个简单的方式，假设agent_id是固定的或者从context中获取
        self.agent_id = msg.agent_id
        if msg.task_path:
            self._task_path: Optional[str] = msg.task_path  
        else:
            self._task_path = ""

        from agents.tree.tree_manager import TreeManager
        tree_manager = TreeManager()
        self.meta=tree_manager.get_agent_meta(self.agent_id)
        try:
            # 使用新的能力获取方式
            self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
            # self.conversation_manager = get_capability("conversation", expected_type=IConversationManagerCapability)
            self.task_planner = get_capability("task_planning", expected_type=ITaskPlanningCapability)
            
            self.log = logging.getLogger(f"AgentActor_{self.agent_id}")
            self.log.info(f"AgentActor initialized for {self.agent_id}")
            # 不需要发送初始化响应，因为任务处理会返回结果
        except Exception as e:
            self.log.error(f"Failed to initialize capabilities for agent {self.agent_id}: {e}")
            # 初始化失败时，后续任务处理会捕获异常

    def _handle_task(self, task: AgentTaskMessage, sender: ActorAddress):
        """
        主任务处理入口（后台）：专注于任务执行

        流程说明:
        0-是否是参数补完逻辑
        ② 任务操作分类
        ③ 根据操作类型分发
        ④ 节点选择
        ⑤ 任务规划
        ⑥ 并行判断
        ⑦ 构建TaskGroupRequest
        ⑧ 等待结果聚合
        """
        if not self._ensure_memory_ready():
            return

        # 获取任务信息
        user_input = str(task.content) + str(task.description or "")
        user_id = task.user_id
        parent_task_id = task.task_id
        reply_to = task.reply_to or sender  # 前台要求回复的地址

        if not parent_task_id:
            self.log.error("Missing task_id in agent_task")
            return

        self.task_id_to_sender[parent_task_id] = reply_to
        self.current_user_id = user_id

        self.log.info(f"[AgentActor] Handling task {parent_task_id}: {user_input[:50]}...")

        # --- 流程 0: 参数补完检查 ---
        # 如果是参数补完消息，直接分发给对应的ExecutionActor
        if task.is_parameter_completion:
            self.log.info(f"[AgentActor] Detected parameter completion for task {parent_task_id}")
            # 直接调用恢复逻辑
            parameters = task.parameters
            self._resume_paused_task(parent_task_id, parameters, reply_to)
            return

        # --- 流程 ②: 任务操作分类 ---
        operation_result = self._classify_task_operation(user_input, {})

        # --- 流程 ③: 根据操作类型分发 ---
        self._dispatch_operation(operation_result, task, reply_to)

    def _dispatch_operation(self, operation_result: Dict[str, Any], task: AgentTaskMessage, sender: ActorAddress):
        """
        ③ 操作分发 - 根据操作类型执行不同的处理逻辑

        Args:
            operation_result: 操作分类结果
            task: 任务信息
            sender: 发送者地址
        """
        operation_type = operation_result["operation_type"]
        category = operation_result["category"]
        parent_task_id = task.task_id
        user_input = str(task.content) + str(task.description or "")

        self.log.info(f"[AgentActor] Dispatching operation: {operation_type.value}, category: {category.value}")


        if category == TaskOperationCategory.CREATION:
            # 创建类 → 继续任务执行流程
            if operation_type == TaskOperationType.NEW_TASK:
                self._handle_task_creation(task.__dict__, sender)
            if operation_type == TaskOperationType.NEW_DELAYED_TASK:
                self._handle_delayed_task_creation(task.__dict__, sender)
            if operation_type == TaskOperationType.NEW_SCHEDULED_TASK:
                self._handle_scheduled_task_creation(task.__dict__, sender)

        elif category == TaskOperationCategory.EXECUTION:
            # 执行控制类 → 执行对应操作
            self._handle_execution_control(operation_type, operation_result, task.__dict__, sender)

        elif category == TaskOperationCategory.LOOP_MANAGEMENT:
            # 循环管理类 → 转发到LoopScheduler
            self._forward_to_loop_scheduler(operation_result, parent_task_id, sender)

        elif category == TaskOperationCategory.MODIFICATION:
            # 修改类 → 执行修改操作
            self._handle_task_modification(operation_type, operation_result, task.__dict__, sender)

        elif category == TaskOperationCategory.QUERY:
            # 查询类 → 查询并返回
            self._handle_task_query(operation_type, operation_result, task.__dict__, sender)

        else:
            # 未知类型
            task_result = TaskResultMessage(
                task_id=parent_task_id,
                result=None,
                error=f"不支持的操作类型: {operation_type.value}",
                message=None
            )
            self.send(sender, task_result)

    def _handle_task_creation(self, task: Dict[str, Any], sender: ActorAddress):
        """
        处理任务创建类操作

        流程:
        ④ 节点选择
        ⑤ 任务规划
        ⑥ 并行判断
        ⑦ 构建TaskGroupRequest
        ⑧ 发送并等待结果
        """


        parent_task_id = task.get("task_id")
        user_input = task.get("content", "") + task.get("description", "")+ str(task.get("context", {}))

        self.log.info(f"[AgentActor] Handling task creation: {user_input[:50]}...")

        decision_context = self.memory_cap.build_conversation_context(self.current_user_id)
        # --- 流程 ⑤: 任务规划 ---
        plans = self._plan_task_execution(user_input, decision_context)  
        for plan in plans:
                # 仅对 AGENT 类型的节点进行判断，MCP 通常是确定性工具
                if plan.get('type') == 'AGENT':
                    # 构造上下文：结合任务本身的描述 + 全局记忆
                    plan_ctx = (
                        f"Task Step: {plan['step']}\n"
                        f"Global Memory: {decision_context or 'None'}\n"
                        f"Params: {plan.get('params')}"
                    )
                    
                    # 调用 LLM 判断
                    strategy = self._llm_decide_should_execute_in_parallel(
                        task_desc=plan.get('description', ''),
                        context=plan_ctx
                    )
                    
                    # 标记结果
                    plan['is_parallel'] = strategy['is_parallel']
                    plan['strategy_reasoning'] = strategy['reasoning']
                    
                    if plan['is_parallel']:
                        logger.info(f"Task {plan['step']} marked for parallel diversity: {strategy['reasoning']}")
                else:
                    # MCP 默认单次执行
                    plan['is_parallel'] = False      


        # --- 流程 ⑦: 构建TaskGroupRequest ---
        task_group_request = self._build_task_group_request(plans,parent_task_id,user_input )

        # --- 流程 ⑧: 发送给TaskGroupAggregatorActor ---
        self._send_to_task_group_aggregator(task_group_request, sender)

    def _handle_execution_control(self, operation_type, operation_result: Dict[str, Any],
                                  task: Dict[str, Any], sender: ActorAddress):
        """处理执行控制类操作"""
        task_id = task.get("task_id")

        if operation_type == TaskOperationType.EXECUTE_TASK:
            # 立即执行任务
            self._handle_task_creation(task, sender)

        elif operation_type == TaskOperationType.PAUSE_TASK:
            # 暂停任务 - 这里需要实现任务暂停逻辑
            self.log.info(f"Pausing task {task_id}")
            from common.messages.interact_messages import TaskPausedMessage
            pause_msg = TaskPausedMessage(
                task_id=task_id,
                missing_params=[],
                question="任务已暂停"
            )
            self.send(sender, pause_msg)

        elif operation_type == TaskOperationType.RESUME_TASK:
            # 恢复任务
            self._resume_paused_task(task_id, operation_result.get("parameters", {}), sender)

        elif operation_type == TaskOperationType.CANCEL_TASK:
            # 取消任务
            self._handle_cancel_any_task(task, sender)

        elif operation_type == TaskOperationType.RETRY_TASK:
            # 重试任务
            self._handle_re_run_task(task, sender)

        else:
            task_result = TaskResultMessage(
                task_id=task_id,
                result=None,
                error=f"Unsupported execution control operation: {operation_type.value}",
                message=None
            )
            self.send(sender, task_result)

    def _handle_task_modification(self, operation_type, operation_result: Dict[str, Any],
                                  task: Dict[str, Any], sender: ActorAddress):
        """处理任务修改类操作"""
        task_id = task.get("task_id")

        if operation_type == TaskOperationType.COMMENT_ON_TASK:
            comment = operation_result.get("parameters", {}).get("comment", "")
            self._handle_add_comment(task, comment, sender)

        elif operation_type == TaskOperationType.REVISE_RESULT:
            revision = operation_result.get("parameters", {}).get("revision", "")
            self._handle_revise_result(task, revision, sender)

        else:
            task_result = TaskResultMessage(
                task_id=task_id,
                result=None,
                error=f"Unsupported modification operation: {operation_type.value}",
                message=None
            )
            self.send(sender, task_result)

    def _handle_task_query(self, operation_type, operation_result: Dict[str, Any],
                          task: Dict[str, Any], sender: ActorAddress):
        """处理任务查询类操作"""
        task_id = task.get("task_id")

        

        # TODO: 实现查询逻辑
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "message_type": "query_result",
                "result": f"Query operation {operation_type.value} not fully implemented yet"
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)

    
    def _handle_new_task(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str, parent_task_id: str):
        """处理新增任务"""
        # 调用新的_handle_new_task_execution方法
        self._handle_task_creation(task, sender)
    
    def _handle_query_operation(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str):
        """处理查询相关操作"""
        # 这里实现查询相关的逻辑
        task_id = task.get("task_id", "")
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "status": "query_result",
                "message": f"查询结果：{current_desc}"
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _handle_chat_operation(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str):
        """处理闲聊相关操作"""
        # 这里实现闲聊相关的逻辑
        task_id = task.get("task_id", "")
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "status": "chat_response",
                "message": f"闲聊回复：{current_desc}"
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _classify_task_operation(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        ② 任务操作分类 - 使用TaskOperationCapability分类任务操作

        Args:
            user_input: 用户输入
            context: 上下文信息

        Returns:
            Dict containing:
            - operation_type: TaskOperationType (操作类型)
            - category: TaskOperationCategory (操作类别)
            - target_task_id: Optional[str] (目标任务ID)
            - parameters: Dict[str, Any] (提取的参数)
            - confidence: float (置信度)
        """
        try:
            # 使用TaskOperationCapability进行分类
            task_op_cap:ITaskOperationCapability = get_capability("task_operation", expected_type=ITaskOperationCapability)

            if task_op_cap:

                return task_op_cap.classify_operation(user_input, context)
                
            else:
                # Fallback: 默认为新任务
                return {
                    "operation_type": TaskOperationType.NEW_TASK,
                    "category": TaskOperationCategory.CREATION,
                    "target_task_id": None,
                    "parameters": {},
                    "confidence": 0.5
                }
        except Exception as e:
            self.log.warning(f"Task operation classification failed: {e}. Falling back to NEW_TASK.")
            return {
                "operation_type": TaskOperationType.NEW_TASK,
                "category": TaskOperationCategory.CREATION,
                "target_task_id": None,
                "parameters": {},
                "confidence": 0.0,
                "error": str(e)
            }
    
    def _resume_paused_task(self, task_id: str, parameters: Dict[str, Any], sender: ActorAddress):
        """
        恢复暂停的任务链并继续执行

        Args:
            task_id: 任务ID
            parameters: 补充完成的参数
            sender: 发送者（前台InteractionActor）
        """
        self.log.info(f"Resuming paused task {task_id} with parameters: {list(parameters.keys())}")

        # 发布任务恢复事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_RESUMED.value,
            source="AgentActor",
            agent_id=self.agent_id,
            data={"parameters": list(parameters.keys())}
        )

        # 关键：从映射中获取原来的ExecutionActor地址
        exec_actor = self.task_id_to_execution_actor.get(task_id)

        if not exec_actor:
            self.log.error(f"Cannot find ExecutionActor for task {task_id}, task cannot be resumed")
            # 通知前台恢复失败
            task_result = TaskResultMessage(
                task_id=task_id,
                result=None,
                error="Cannot find the ExecutionActor for this task",
                message=None
            )
            self.send(sender, task_result)
            return

        # 构建恢复消息，发送到原来的ExecutionActor
        exec_request = {
            "type": "resume_execution",
            "task_id": task_id,
            "parameters": parameters,
            "reply_to": self.myAddress
        }

        self.log.info(f"Sending resume request to original ExecutionActor for task {task_id}")
        self.send(exec_actor, exec_request)

        # 记录sender以便接收结果（更新，因为可能是新的前台请求）
        self.task_id_to_sender[task_id] = sender

    def _handle_resume_task(self, message: ResumeTaskMessage, sender: ActorAddress):
        """
        处理来自前台的resume_task消息

        Args:
            message: 包含task_id, parameters, user_id, reply_to
            sender: 发送者
        """
        task_id = message.task_id
        parameters = message.parameters
        user_id = message.user_id
        reply_to = message.reply_to or sender

        self.log.info(f"Received resume task request for {task_id} from InteractionActor")

        # 记录reply_to以便回复前台
        self.task_id_to_sender[task_id] = reply_to

        # 调用恢复逻辑
        self._resume_paused_task(task_id, parameters, reply_to)

    def _handle_task_paused_from_execution(self, message: Any, sender: ActorAddress):
        """
        处理来自ExecutionActor的task_paused消息，现在改为处理NEED_INPUT状态并使用TaskCompletedMessage向上报告

        Args:
            message: 包含task_id, missing_params, question, execution_actor_address
            sender: ExecutionActor的地址
        """
        task_id = message.task_id
        missing_params = getattr(message, "missing_params", [])
        question = getattr(message, "question", "")
        execution_actor_address = getattr(message, "execution_actor_address", None)

        self.log.info(f"Task {task_id} needs input by ExecutionActor, forwarding with TaskCompletedMessage")

        # 重要：保存ExecutionActor地址到映射，以便恢复时能找到
        if execution_actor_address:
            self.task_id_to_execution_actor[task_id] = execution_actor_address
            self.log.info(f"Saved ExecutionActor address for task {task_id}")
        else:
            self.log.warning(f"No execution_actor_address in need_input message for task {task_id}")

        # 构建TaskCompletedMessage
        task_result = TaskCompletedMessage(
            task_id=task_id,
            status="NEED_INPUT",
            result={
                "missing_params": missing_params,
                "question": question
            },
            agent_id=self.agent_id
        )

        # 如果有聚合器，通知聚合器
        if self.current_aggregator:
            self.send(self.current_aggregator, task_result)
        else:
            # 否则，直接返回给前台InteractionActor
            original_sender = self.task_id_to_sender.get(task_id, sender)
            if original_sender:
                # 构建前台交互消息，使用InteractTaskPausedMessage
                frontend_paused_msg = InteractTaskPausedMessage(
                    task_id=task_id,
                    missing_params=missing_params,
                    question=question
                )
                self.send(original_sender, frontend_paused_msg)
            else:
                self.log.warning(f"No reply_to address found for task {task_id}, cannot forward need_input message")

    def _handle_loop_task_setup(self, task: Dict[str, Any], sender: ActorAddress):
        """处理循环任务设置"""
        # 调用现有的add_loop_task方法
        self.add_loop_task(task, sender)
    

    
    def _should_optimize(self) -> bool:
        """判断是否需要优化"""
        # 简单实现：默认不需要优化
        ## TODO: 待实现
        return True
    



    def _plan_task_execution(self, task_description: str, memory_context: str = None) -> Dict[str, Any]:
        """
        ⑤ 任务规划 - 使用TaskPlanner生成执行计划

        Args:
            task_description: 任务描述

        Returns:
            执行计划，包含subtasks, dependencies, parallel_groups
        """
        try:
            if not self.task_planner:
                from capabilities.task_planning.interface import ITaskPlanningCapability
                self.task_planner: ITaskPlanningCapability = get_capability("task_planning", expected_type=ITaskPlanningCapability)
            
            # 使用TaskPlanner生成计划
            subtasks = self.task_planner.generate_execution_plan(self.agent_id,task_description,memory_context)
            return subtasks
        except Exception as e:
            self.log.warning(f"Task planning failed: {e}")

        # Fallback: 返回None，让调用者创建简单计划
        return None



    def _build_task_group_request(
        self, 
        tasks: List[Dict[str, Any]], 
        parent_task_id: str,
        context: str,
    ) :
        from common.messages.task_messages import TaskSpec, TaskGroupRequestMessage

        task_specs = []
        for task in tasks:
            # 防御性处理：确保必要字段存在
            task_clean = {
                "step": int(task.get("step", 0)),
                "type": task.get("type", "unknown"),
                "executor": task.get("executor", "unknown"),
                "description": task.get("description", ""),  # ← 关键修复
                "params": str(task.get("params", "")),
                "is_parallel": bool(task.get("is_parallel", False)),
                "strategy_reasoning": task.get("strategy_reasoning", ""),
                "is_dependency_expanded": bool(task.get("is_dependency_expanded", False)),
                "original_parent": task.get("original_parent"),
                "user_id": self.current_user_id,
            }

            # 如果你希望保留原始 task 中的其他字段到 extras
            # 可以把多余字段塞进去（可选）
            extra_keys = set(task.keys()) - set(task_clean.keys())
            if extra_keys:
                task_clean.update({k: task[k] for k in extra_keys})

            task_spec = TaskSpec(**task_clean)
            task_specs.append(task_spec)


        request = TaskGroupRequestMessage(
            task_id=str(uuid.uuid4()),           # ← 唯一任务 ID
            trace_id=str(uuid.uuid4()),          # ← 链路追踪 ID（可与 task_id 相同或不同）
            task_path=self._task_path+self.agent_id,      # ← 任务路径，按你系统逻辑填写
            source=getattr(self, "myAddress", "unknown_address"),
            destination="TaskGroupAggregator",
            parent_task_id=parent_task_id,
            subtasks=task_specs,
            strategy="standard",
            original_sender=getattr(self, "myAddress", None),
            context={"above_context": context},
            user_id=self.current_user_id,
        )
        return request
    def _send_to_task_group_aggregator(self, task_group_request, sender: ActorAddress):
        """
        ⑧ 发送到TaskGroupAggregatorActor

        Args:
            task_group_request: 任务组请求
            sender: 原始发送者（用于回复）
        """
        from capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor


        # 创建TaskGroupAggregatorActor
        aggregator = self.createActor(TaskGroupAggregatorActor)

        # 构建标准的TaskGroupRequest
        # group_request = TaskGroupRequest(
        #     source=self.myAddress,
        #     destination=aggregator,
        #     group_id=task_group_request["parent_task_id"],
        #     tasks=task_group_request["subtasks"],
        #     reply_to=sender  # 回复给原始发送者
        # )

        group_request = task_group_request

        self.log.info(f"Sending task group to aggregator")
        self.send(aggregator, group_request)

    
    

    # ======================
    # 子任务结果处理（保持聚合逻辑不变）
    # ======================

    def add_loop_task(self, task: Dict[str, Any], sender: ActorAddress):
        """
        注意：Thespian Actor 是事件驱动的，不能阻塞。
        所以我们不在此启动 pika 消费者！
        而是让外部系统（或另一个 Actor）将 RabbitMQ 消息桥接到 Thespian。
        """
        parent_task_id = task.get("task_id")
        if not parent_task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
            
        current_desc = task.get("description") or task.get("content", "")
        self.log.info(f"Registering LOOP task: {parent_task_id}")
        
        # 构造循环执行的消息（当调度器触发时，会发回给自己）
        loop_execution_msg = {
            "message_type": "execute_loop_task",
            "original_task": task,
            "decision": {"is_loop": True}
        }

        # 向全局调度器注册
        loop_interval = self._estimate_loop_interval(current_desc)
        register_msg = {
            "type": "register_loop_task",
            "task_id": parent_task_id,
            "interval_sec": loop_interval,
            "message": loop_execution_msg
        }

        # 获取全局调度器地址（通过 globalName）
        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, register_msg)

        # 保存循环任务到注册表
        loop_task = Task(
            task_id=parent_task_id,
            description=current_desc,
            task_type=TaskType.LOOP,
            user_id=self.current_user_id,
            schedule=str(loop_interval),
            next_run_time=datetime.now().fromtimestamp(time.time() + loop_interval),
            original_input=current_desc
        )
        # 使用任务规划能力保存任务
        try:
            self.task_planner.task_repo.create_task(loop_task)
        except Exception as e:
            self.log.warning(f"Failed to save loop task: {e}")

        # 回复用户：已注册循环任务
        task_result = TaskResultMessage(
            task_id=parent_task_id,
            result={
                "status": "loop_registered",
                "interval_sec": loop_interval,
                "reasoning": "循环任务已成功注册"
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
        return
    
    def _estimate_loop_interval(self, task_desc: str) -> int:
        """
        估算循环任务的执行间隔
        """
        # 这里可以使用LLM来估算，暂时返回默认值
        return 3600  # 默认1小时



    def _resolve_task_id_by_reference(self, reference: str) -> Optional[str]:
        """根据用户描述（如“日报”）匹配已注册的循环任务ID"""
        # 使用task_registry根据引用查找任务
        task = self.task_registry.find_task_by_reference(self.current_user_id, reference)
        return task.task_id if task else None


    def _handle_trigger_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关循环任务",
                message=None
            )
            self.send(sender, task_result)
            return

        # 向 LoopScheduler 发送“立即执行”消息（自定义类型）
        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "trigger_task_now",
            "task_id": task_id
        })
        task_result = TaskResultMessage(
            task_id=task_id,
            result={"status": "triggered"},
            error=None,
            message=None
        )
        self.send(sender, task_result)

    def _handle_cancel_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关循环任务",
                message=None
            )
            self.send(sender, task_result)
            return

        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "cancel_loop_task",
            "task_id": task_id
        })
        task_result = TaskResultMessage(
            task_id=task_id,
            result={"status": "cancelled"},
            error=None,
            message=None
        )
        self.send(sender, task_result)

    def _handle_modify_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        new_interval = intent.get("new_interval_sec")
        if not new_interval or new_interval <= 0:
            # 让 LLM 估算
            new_interval = self._estimate_loop_interval(intent.get("reasoning", ref))

        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关循环任务",
                message=None
            )
            self.send(sender, task_result)
            return

        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "update_loop_interval",
            "task_id": task_id,
            "interval_sec": int(new_interval)
        })
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "status": "updated",
                "new_interval_sec": new_interval
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)



    def _handle_pause_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        task_id = self._resolve_task_id_by_reference(intent["task_reference"])
        if task_id:
            self._send_to_scheduler({"type": "pause_loop_task", "task_id": task_id}, sender)
        else:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="任务未找到",
                message=None
            )
            self.send(sender, task_result)

    def _handle_resume_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        task_id = self._resolve_task_id_by_reference(intent["task_reference"])
        if task_id:
            self._send_to_scheduler({"type": "resume_loop_task", "task_id": task_id}, sender)
        else:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="任务未找到",
                message=None
            )
            self.send(sender, task_result)

    def _handle_add_comment(self, task: dict, comment: str, sender: ActorAddress):
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
        
        # 使用task_registry添加评论
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关任务",
                message=None
            )
            self.send(sender, task_result)
            return
        
        # 添加评论
        target_task.comments.append({"content": comment, "created_at": datetime.now().isoformat()})
        self.task_registry.update_task(task_id, {"comments": target_task.comments})
        task_result = TaskResultMessage(
            task_id=task_id,
            result={"status": "comment_added"},
            error=None,
            message=None
        )
        self.send(sender, task_result)

    def _handle_revise_result(self, task: dict, new_content: str, sender: ActorAddress):
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
        
        # 使用task_registry修改结果
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关任务",
                message=None
            )
            self.send(sender, task_result)
            return
        
        # 简单策略：全量替换；高级策略：结构化 patch
        self.task_registry.update_task(task_id, {"corrected_result": new_content})
        task_result = TaskResultMessage(
            task_id=task_id,
            result={"status": "result_revised"},
            error=None,
            message=None
        )
        self.send(sender, task_result)

    def _handle_re_run_task(self, task: dict, sender: ActorAddress):
        # 重新提交原任务描述
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
        
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关任务",
                message=None
            )
            self.send(sender, task_result)
            return
        
        new_task_msg = {
            "task_id": f"{task_id}_retry_{int(time.time())}",
            "description": target_task.description,
            "original_task_id": task_id,  # 用于追踪
            "user_id": self.current_user_id
        }
        
        # 使用_handle_new_task重新执行任务
        self._handle_new_task(new_task_msg, sender, target_task.description, new_task_msg["task_id"])
    
    def _handle_cancel_any_task(self, task: dict, sender: ActorAddress):
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
        
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关任务",
                message=None
            )
            self.send(sender, task_result)
            return
        
        if target_task.type == TaskType.LOOP:
            self._forward_to_loop_scheduler({"type": "cancel_loop_task", "task_id": task_id}, sender)
        else:
            # 普通任务：标记为 cancelled（若还在运行，可发取消信号）
            self.task_registry.update_task(task_id, {"status": "cancelled"})
            task_result = TaskResultMessage(
                task_id=task_id,
                result={"status": "task_cancelled"},
                error=None,
                message=None
            )
            self.send(sender, task_result)
    
    def _forward_to_loop_scheduler(self, intent: Dict[str, Any], task_id: str, sender: ActorAddress):
        """转发给循环调度器"""
        # 获取全局调度器地址（通过 globalName）
        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        
        # 构造转发消息
        forward_msg = {
            "type": intent.get("type", "trigger_task_now"),
            "task_id": task_id
        }
        
        # 添加额外参数
        if intent.get("type") == "update_loop_interval":
            forward_msg["interval_sec"] = intent.get("new_interval_sec", 3600)
        
        self.send(loop_scheduler, forward_msg)
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "status": "command_sent",
                "command": forward_msg["type"]
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)



   
   
    def _send_to_scheduler(self, msg: dict, reply_to: ActorAddress):
        scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(scheduler, msg)
        # 可选：等待响应或直接回复
        task_result = TaskResultMessage(
            task_id=msg.get("task_id", ""),
            result={
                "status": "command_sent",
                "command": msg.get("type", "")
            },
            error=None,
            message=None
        )
        self.send(reply_to, task_result)

    def _handle_task_result(self, result_msg: TaskCompletedMessage, sender: ActorAddress):
        """统一处理任务结果（成功、失败、错误、需要输入），使用TaskCompletedMessage向上报告"""
        task_id = result_msg.task_id
        result_data = result_msg.result
        status = result_msg.status

        # 1. 发送优化反馈
        # self._send_optimization_feedback(task_id, result_msg, success=status == "SUCCESS")

        if self.current_aggregator:
            # 2. 如果有聚合器，通知聚合器
            self.send(self.current_aggregator, result_msg)
        else:
            # 3. 如果是根任务，直接返回给前台InteractionActor
            original_sender = self.task_id_to_sender.get(task_id, sender)

            # 构建前台交互消息，使用TaskResultMessage
            error_str = None
            if isinstance(result_data, dict) and "error" in result_data:
                error_str = str(result_data["error"])
            elif hasattr(result_msg, "error") and result_msg.error:
                error_str = str(result_msg.error)
            
            # 构建TaskResultMessage
            task_result = TaskResultMessage(
                task_id=task_id,
                trace_id=result_msg.trace_id,
                task_path=result_msg.task_path,
                result=result_data,
                error=error_str,
                message=None
            )

            self.send(original_sender, task_result)

            # 4. 发布事件
            from events.event_bus import event_bus
            from events.event_types import EventType
            event_type = EventType.TASK_COMPLETED.value if status == "SUCCESS" else EventType.TASK_FAILED.value
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=event_type,
                source="AgentActor",
                agent_id=self.agent_id,
                data={"result": result_data}
            )

            # 5. 清理映射
            self.task_id_to_sender.pop(task_id, None)
            self.task_id_to_execution_actor.pop(task_id, None)

    def _send_optimization_feedback(self, task_id: str, result_msg: Any, success: bool):
        """
        发送优化反馈给OptimizerActor

        仅当任务是循环任务且启用优化时发送
        """
        try:
            # 检查是否是循环任务（可以从task_id或任务注册表查询）
            # 这里简化处理：假设所有loop相关的任务都发送反馈
            # 实际实现中应该查询任务类型

            # 构建执行记录
            import time
            from datetime import datetime

            # 处理不同类型的result_msg
            if hasattr(result_msg, "result"):
                result_data = result_msg.result
                parameters = getattr(result_msg, "parameters", {})
            else:
                result_data = result_msg.get("result", {})
                parameters = result_msg.get("parameters", {})

            execution_record = {
                "execution_time": datetime.now().isoformat(),
                "parameters": parameters,
                "result": result_data,
                "success": success,
                "duration": result_data.get("duration", 0.0) if isinstance(result_data, dict) else 0.0,
                "score": self._calculate_execution_score(result_data, success),
                "error": result_data.get("error") if isinstance(result_data, dict) and not success else None
            }

            # 发送给OptimizerActor
            from capability_actors.optimizer_actor import OptimizerActor

            optimizer = self.createActor(OptimizerActor, globalName="optimizer_actor")

            self.send(optimizer, {
                "type": "execution_feedback",
                "task_id": task_id,
                "execution_record": execution_record
            })

            self.log.debug(f"Sent optimization feedback for task {task_id}")

        except Exception as e:
            # 优化反馈失败不应该影响主流程
            self.log.warning(f"Failed to send optimization feedback for task {task_id}: {e}")

    def _calculate_execution_score(self, result_data: Any, success: bool) -> float:
        """
        计算执行分数
        
        Args:
            result_data: 执行结果数据
            success: 是否成功

        Returns:
            0.0-1.0之间的分数
        """

        ##TODO：使用LLM
        if not success:
            return 0.0

        # 基础分数
        base_score = 0.7

        # 根据执行时间调整
        duration = 0.0
        if isinstance(result_data, dict):
            duration = result_data.get("duration", 0.0)
        
        if duration < 1.0:
            base_score += 0.2
        elif duration > 10.0:
            base_score -= 0.2

        # 根据结果质量调整（如果有）
        quality_score = None
        if isinstance(result_data, dict):
            quality_score = result_data.get("quality_score")
        
        if quality_score is not None:
            base_score = (base_score + quality_score) / 2

        # 确保在0-1范围内
        return max(0.0, min(1.0, base_score))
    




    # ======================
    # 私有辅助方法（按职责拆分）
    # ======================

    def _ensure_memory_ready(self) -> bool:

        if self.memory_cap is None:
            self.log.error("Memory capability not ready")
            return False
        return True

  

    def _dispatch_subtasks(
        self,
        plan: List[Dict[str, Any]],
        parent_task_id: str,
        original_desc: str,
        needs_vault: bool
    ) -> Set[str]:
        """
        ⑦ 任务分发 - 直接发给 TaskGroupAggregatorActor 进行批量管理
        """
        pending = set()

        # 创建 TaskGroupAggregatorActor
        from capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor
        from common.messages.task_messages import TaskGroupRequest, TaskSpec

        task_group_addr = self.createActor(TaskGroupAggregatorActor)

        # 构建任务规范列表
        task_specs = []
        for i, step in enumerate(plan):
            child_cap = step["node_id"]
            child_task_id = f"{parent_task_id}.child_{i}"
            child_desc = step.get("description", "")

            child_memory_ctx = self.memory_cap.build_execution_context(
                task_description=child_desc,
                include_sensitive=needs_vault
            )

            final_child_context = {
                "memory_context": child_memory_ctx,
                "instructions": step.get("intent_params", {}),
                "original_task": original_desc,
                "capability": child_cap
            }

            # 创建任务规范
            task_spec = TaskSpec(
                task_id=child_task_id,
                type=child_cap,  # 能力类型
                parameters=final_child_context,
                repeat_count=1,
                aggregation_strategy="single"
            )
            task_specs.append(task_spec)
            pending.add(child_task_id)

            self._report_event("subtask_spawned", child_task_id, {
                "parent_task_id": parent_task_id,
                "capability": child_cap
            })

        # 创建任务组请求
        group_request = TaskGroupRequest(
            source=self.myAddress,
            destination=task_group_addr,
            group_id=parent_task_id,
            tasks=task_specs,
            reply_to=self.myAddress
        )

        # 发送任务组到 TaskGroupAggregatorActor
        self.send(task_group_addr, group_request)

        return pending






    def _llm_decide_should_execute_in_parallel(self, task_desc: str, context: str) -> Dict[str, Any]:

        """
        使用 Qwen 判断任务策略：
        - 是否应并行执行（如生成多个创意方案）

        返回 dict 包含:
          is_parallel: bool
          reasoning: str (LLM 的思考过程)
        """

        return  {
                "is_parallel": False,
                "reasoning": f"Failed to analyze due to error. Using default strategy."
            }

        prompt = f"""你是一个智能任务分析器。请根据以下信息判断当前任务是否需要【多样性发散执行】。
所谓“多样性发散”，指是否需要生成多个不同的创意、方案或草稿供后续选择。

【当前任务描述】
{task_desc}

【相关记忆与上下文】
{context}

请严格按以下 JSON 格式输出，不要包含任何额外内容：
{{
"is_parallel": false,
"reasoning": "简要说明判断依据"
}}
"""

        try:
            # 使用新的能力获取方式获取LLM能力
            llm = get_capability("llm", expected_type=ILLMCapability)
            result = llm.generate(prompt, parse_json=True, max_tokens=300)

            # 确保字段存在且类型正确
            return {
                "is_parallel": bool(result.get("is_parallel", False)),
                "reasoning": str(result.get("reasoning", "No reasoning provided."))
            }

        except Exception as e:
            self.log.error(f"Error in _llm_decide_task_strategy: {e}")
            # 安全回退
            return {
                "is_parallel": False,
                "reasoning": f"Failed to analyze due to error: {str(e)}. Using default strategy."
            }


    def _report_event(self, event_type: str, task_id: str, details: Dict[str, Any]):
        self.log.info(f"[{event_type}] {task_id}: {details}")

    def _report_error(self, task_id: str, error: str, sender: ActorAddress):
        self.send(sender, TaskCompletedMessage(
            task_id=task_id,
            result={"error": {"message": error}},
            status="ERROR",
            agent_id=self.agent_id
        ))

