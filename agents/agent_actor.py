import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from thespian.actors import Actor, ActorAddress

from capability_actors.mcp_actor import MCPCapabilityActor
from common.messages import SubtaskResultMessage, SubtaskErrorMessage, TaskMessage, McpFallbackRequest

# 导入新的能力管理模块
from capabilities import init_capabilities, get_capability, get_capability_registry

# 导入能力接口
from capabilities.llm.interface import ILLMCapability
from capabilities.llm_memory.interface import IMemoryCapability
from capabilities.routing.interface import ITaskRouter
from capabilities.decision.interface import ITaskStrategyCapability, ITaskOperationCapability

# 导入类型定义
from common.types.draft import TaskDraft
from common.types.intent import IntentResult, IntentType
from common.types.task import Task, TaskType, TaskStatus
from common.types.task_operation import TaskOperationType, TaskOperationCategory

# 导入新的能力接口
from capabilities.cognition.intent_router import IIntentRouterCapability
from capabilities.context.interface import IConversationManagerCapability
from capabilities.decision.task_planner import ITaskPlannerCapability

# 导入循环调度器
from capability_actors.loop_scheduler_actor import LoopSchedulerActor

# 导入事件总线
from events.event_bus import event_bus
from events.event_types import EventType



TASK_INTENTS = {
    "new_task",               # 全新任务
    "comment_on_task",        # 追加评论
    "revise_result",          # 修改结果
    "re_run_task",            # 重新执行
    "cancel_task",            # 取消（包括循环和普通）
    "archive_task",           # 归档
    # 循环专属
    "trigger_existing",
    "modify_loop_interval",
    "pause_loop",
    "resume_loop"
}


##TODO：需要完整的任务管理器
# class TaskManager:
#     def get_recent_tasks(self, limit=10) -> List[Dict]: ...
#     def get_task_by_id(self, task_id: str) -> Optional[Dict]: ...
#     def add_comment_to_task(self, task_id: str, comment: str): ...
#     def update_task_result(self, task_id: str, new_result): ...
#     def mark_task_cancelled(self, task_id: str): ...
#     def archive_task(self, task_id: str): ...




##后台

class AgentActor(Actor):
    def __init__(self):
        super().__init__()
        self.agent_id: str = ""
        self.memory_cap: Optional[IMemoryCapability] = None

        self._aggregation_state: Dict[str, Dict] = {}
        self.task_id_to_sender: Dict[str, ActorAddress] = {}
        # 新增：保存task_id到ExecutionActor地址的映射（用于恢复暂停的任务）
        self.task_id_to_execution_actor: Dict[str, ActorAddress] = {}
        self.log = logging.getLogger("AgentActor")  # 初始日志，后续按 agent_id 覆盖

        # 添加澄清选项状态
        self.clarification_options: Optional[List[Dict[str, str]]] = None

        # 添加当前用户ID（实际应从消息中获取）
        self.current_user_id: Optional[str] = None

        # 初始化能力实例引用
        self.conversation_manager: Optional[IConversationManagerCapability] = None
        self.intent_router: Optional[IIntentRouterCapability] = None
        self.task_planner: Optional[ITaskPlannerCapability] = None

        # 添加当前聚合器和原始客户端地址
        self.current_aggregator = None
        self.original_client_addr = None

        # 初始化能力管理
        self.capability_manager = init_capabilities()
        self.capability_registry = get_capability_registry()

        # 初始化能力实例
        self.task_router: Optional[ITaskRouter] = None
        self.task_planner: Optional[Any] = None

    def receiveMessage(self, message: Any, sender: ActorAddress):
        try:
            if isinstance(message, dict) and "message_type" in message:
                msg_type = message["message_type"]
                handlers = {
                    "init": self._handle_init,
                    "agent_task": self._handle_task,
                    "resume_task": self._handle_resume_task,
                    "task_paused": self._handle_task_paused_from_execution,
                    "subtask_result": self._handle_execution_result,
                    "subtask_error": self._handle_execution_error,
                }
                handler = handlers.get(msg_type)
                if handler:
                    handler(message, sender)
                else:
                    self.log.warning(f"Unknown message type: {msg_type}")
            elif isinstance(message, (SubtaskResult, SubtaskError)):
                self._handle_execution_message(message.__dict__, sender)
            else:
                self.log.warning(f"Unknown message type: {type(message)}")
        except Exception as e:
            self.log.exception(f"Error in AgentActor {self.agent_id}: {e}")

    def _handle_init(self, msg: Dict[str, Any], sender: ActorAddress):
        self.agent_id = msg["agent_id"]
        
        try:
            # 使用新的能力获取方式
            self.memory_cap = get_capability("core_memory", expected_type=IMemoryCapability)
            self.intent_router = get_capability("intent_router", expected_type=IIntentRouterCapability)
            self.conversation_manager = get_capability("conversation_manager", expected_type=IConversationManagerCapability)
            self.task_planner = get_capability("task_planner", expected_type=ITaskPlannerCapability)
            
            self.log = logging.getLogger(f"AgentActor_{self.agent_id}")
            self.log.info(f"AgentActor initialized for {self.agent_id}")
            self.send(sender, {"status": "initialized", "agent_id": self.agent_id})
        except Exception as e:
            self.log.error(f"Failed to initialize capabilities for agent {self.agent_id}: {e}")
            self.send(sender, {"status": "init_failed", "agent_id": self.agent_id, "error": str(e)})
            return

    def _handle_task(self, task: Dict[str, Any], sender: ActorAddress):
        """
        主任务处理入口（后台）：专注于任务执行

        流程说明:
        0-是否是参数补完逻辑
        ① 检查是否为叶子节点
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
        user_input = task.get("content", task.get("description", ""))
        user_id = task.get("user_id", "default_user")
        parent_task_id = task.get("task_id")
        reply_to = task.get("reply_to", sender)  # 前台要求回复的地址

        if not parent_task_id:
            self.log.error("Missing task_id in agent_task")
            return

        self.task_id_to_sender[parent_task_id] = reply_to
        self.current_user_id = user_id

        self.log.info(f"[AgentActor] Handling task {parent_task_id}: {user_input[:50]}...")

        # --- 流程 0: 参数补完检查 ---
        # 如果是参数补完消息，直接分发给对应的ExecutionActor
        if task.get("is_parameter_completion", False):
            self.log.info(f"[AgentActor] Detected parameter completion for task {parent_task_id}")
            # 直接调用恢复逻辑
            parameters = task.get("parameters", {})
            self._resume_paused_task(parent_task_id, parameters, reply_to)
            return

        # --- 流程 ①: 叶子节点检查 ---
        if self._is_leaf_node(self.agent_id):
            self.log.info(f"[AgentActor] Agent {self.agent_id} is a leaf node, executing directly")
            self._execute_as_leaf(task, reply_to)
            return

        # --- 流程 ②: 任务操作分类 ---
        operation_result = self._classify_task_operation(user_input, {})

        # --- 流程 ③: 根据操作类型分发 ---
        self._dispatch_operation(operation_result, task, reply_to)

    def _dispatch_operation(self, operation_result: Dict[str, Any], task: Dict[str, Any], sender: ActorAddress):
        """
        ③ 操作分发 - 根据操作类型执行不同的处理逻辑

        Args:
            operation_result: 操作分类结果
            task: 任务信息
            sender: 发送者地址
        """
        operation_type = operation_result["operation_type"]
        category = operation_result["category"]
        parent_task_id = task.get("task_id")
        user_input = task.get("content", task.get("description", ""))

        self.log.info(f"[AgentActor] Dispatching operation: {operation_type.value}, category: {category.value}")

        if category == TaskOperationCategory.CREATION:
            # 创建类 → 继续任务执行流程
            self._handle_task_creation(task, sender)

        elif category == TaskOperationCategory.EXECUTION:
            # 执行控制类 → 执行对应操作
            self._handle_execution_control(operation_type, operation_result, task, sender)

        elif category == TaskOperationCategory.LOOP_MANAGEMENT:
            # 循环管理类 → 转发到LoopScheduler
            self._forward_to_loop_scheduler(operation_result, parent_task_id, sender)

        elif category == TaskOperationCategory.MODIFICATION:
            # 修改类 → 执行修改操作
            self._handle_task_modification(operation_type, operation_result, task, sender)

        elif category == TaskOperationCategory.QUERY:
            # 查询类 → 查询并返回
            self._handle_task_query(operation_type, operation_result, task, sender)

        else:
            # 未知类型
            self.send(sender, {
                "message_type": "task_error",
                "task_id": parent_task_id,
                "error": f"不支持的操作类型: {operation_type.value}"
            })

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
        user_input = task.get("content", task.get("description", ""))

        self.log.info(f"[AgentActor] Handling task creation: {user_input[:50]}...")

        # --- 流程 ④: 节点选择 ---
        selected_node = self._select_execution_node(user_input)

        if not selected_node:
            # 没有找到合适节点，使用MCP Fallback
            self.log.info(f"[AgentActor] No suitable node found, using MCP fallback")
            self._execute_with_mcp_fallback(task, sender)
            return

        self.log.info(f"[AgentActor] Selected node: {selected_node}")

        # --- 流程 ⑤: 任务规划 ---
        plan = self._plan_task_execution(user_input)

        if not plan or not plan.get("subtasks"):
            # 如果没有子任务计划，创建简单的单任务计划
            plan = {
                "subtasks": [{"description": user_input, "node_id": selected_node}],
                "dependencies": [],
                "parallel_groups": []
            }

        # --- 流程 ⑥: 并行判断 ---
        should_parallel = self._should_execute_in_parallel(plan.get("subtasks", []))

        # --- 流程 ⑦: 构建TaskGroupRequest ---
        task_group_request = self._build_task_group_request(plan, parent_task_id, should_parallel)

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
            self.send(sender, {
                "message_type": "task_paused",
                "task_id": task_id,
                "status": "paused"
            })

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
            self.send(sender, {
                "message_type": "task_error",
                "task_id": task_id,
                "error": f"Unsupported execution control operation: {operation_type.value}"
            })

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
            self.send(sender, {
                "message_type": "task_error",
                "task_id": task_id,
                "error": f"Unsupported modification operation: {operation_type.value}"
            })

    def _handle_task_query(self, operation_type, operation_result: Dict[str, Any],
                          task: Dict[str, Any], sender: ActorAddress):
        """处理任务查询类操作"""
        task_id = task.get("task_id")

        # TODO: 实现查询逻辑
        self.send(sender, {
            "message_type": "query_result",
            "task_id": task_id,
            "result": f"Query operation {operation_type.value} not fully implemented yet"
        })

    def _handle_task_operation(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str, parent_task_id: str):
        """处理任务相关操作 (已废弃 - 逻辑已合并到 _handle_task)"""
        # 此方法已不再使用，保留用于向后兼容
        pass
    
    def _handle_new_task(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str, parent_task_id: str):
        """处理新增任务"""
        # 调用新的_handle_new_task_execution方法
        self._handle_new_task_execution(task, sender)
    
    def _handle_query_operation(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str):
        """处理查询相关操作"""
        # 这里实现查询相关的逻辑
        self.send(sender, {
            "status": "query_result",
            "message": f"查询结果：{current_desc}"
        })
    
    def _handle_chat_operation(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str):
        """处理闲聊相关操作"""
        # 这里实现闲聊相关的逻辑
        self.send(sender, {
            "status": "chat_response",
            "message": f"闲聊回复：{current_desc}"
        })
    
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
            task_op_cap = get_capability("task_operation", expected_type=ITaskOperationCapability)

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
            self.send(sender, {
                "message_type": "task_error",
                "task_id": task_id,
                "error": "Cannot find the ExecutionActor for this task"
            })
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

    def _handle_resume_task(self, message: Dict[str, Any], sender: ActorAddress):
        """
        处理来自前台的resume_task消息

        Args:
            message: 包含task_id, parameters, user_id, reply_to
            sender: 发送者
        """
        task_id = message.get("task_id")
        parameters = message.get("parameters", {})
        user_id = message.get("user_id", "default_user")
        reply_to = message.get("reply_to", sender)

        self.log.info(f"Received resume task request for {task_id} from InteractionActor")

        # 记录reply_to以便回复前台
        self.task_id_to_sender[task_id] = reply_to

        # 调用恢复逻辑
        self._resume_paused_task(task_id, parameters, reply_to)

    def _handle_task_paused_from_execution(self, message: Dict[str, Any], sender: ActorAddress):
        """
        处理来自ExecutionActor的task_paused消息，转发给前台InteractionActor

        Args:
            message: 包含task_id, missing_params, question, execution_actor_address
            sender: ExecutionActor的地址
        """
        task_id = message.get("task_id")
        missing_params = message.get("missing_params", [])
        question = message.get("question", "")
        execution_actor_address = message.get("execution_actor_address")

        self.log.info(f"Task {task_id} paused by ExecutionActor, forwarding to InteractionActor")

        # 重要：保存ExecutionActor地址到映射，以便恢复时能找到
        if execution_actor_address:
            self.task_id_to_execution_actor[task_id] = execution_actor_address
            self.log.info(f"Saved ExecutionActor address for task {task_id}")
        else:
            self.log.warning(f"No execution_actor_address in pause message for task {task_id}")

        # 找到对应的前台地址
        reply_to = self.task_id_to_sender.get(task_id)

        if reply_to:
            # 转发暂停消息给前台（不需要包含execution_actor_address）
            frontend_message = {
                "message_type": "task_paused",
                "task_id": task_id,
                "missing_params": missing_params,
                "question": question
            }
            self.send(reply_to, frontend_message)
        else:
            self.log.warning(f"No reply_to address found for task {task_id}, cannot forward pause message")

    def _handle_loop_task_setup(self, task: Dict[str, Any], sender: ActorAddress):
        """处理循环任务设置"""
        # 调用现有的add_loop_task方法
        self.add_loop_task(task, sender)
    
    def _handle_new_task_execution(self, task: Dict[str, Any], sender: ActorAddress):
        """处理新任务执行"""
        # 获取当前任务描述
        current_desc = task.get("description") or task.get("content", "")
        parent_task_id = task.get("task_id")
        
        # === Step 1: 循环任务检测 ===
        decision_context = self.memory_cap.build_conversation_context(current_input=current_desc)
        decision = self._llm_decide_task_strategy(current_desc, decision_context)
        
        if decision.get("is_loop", False):
            self.add_loop_task(task, sender)
            return
        
        # === Step 2: 能力路由 ===
        routing_result = None
        try:
            # 使用新的能力获取方式获取任务路由器
            self.task_router = get_capability("routing", expected_type=ITaskRouter)
            if self.task_router:
                routing_result = self.task_router.select_best_actor(current_desc, context={})
        except Exception as e:
            self.log.warning(f"Failed to get task router: {e}")
        
        if not routing_result:
            # 如果routing_result为空则调用MCPactor做执行
            from capability_actors.mcp_actor import MCPCapabilityActor
            mcp_actor = self.createActor(MCPCapabilityActor)
            self.send(mcp_actor, {
                "type": "execute_task",
                "task_id": parent_task_id,
                "task_type": "leaf_task",
                "context": {
                    "memory_context": decision_context,
                    "instructions": {},
                    "original_task": current_desc,
                    "capability": "mcp"
                },
                "capabilities": {
                    "name": "mcp"
                }
            })
            return
        
        # === Step 3: 判断是否为叶子节点 ===
        if self._is_leaf_node(routing_result):
            # --- 叶子节点路径 ---
            self._execute_leaf_logic(task, sender)
        else:
            # --- 管理节点路径 (流程 ⑥ 任务规划) ---
            # 调用 capabilities/decision/task_planner.py
            subtasks = None
            try:
                # 使用新的能力获取方式获取任务规划器
                self.task_planner = get_capability("planning", expected_type=Any)
                if self.task_planner:
                    subtasks = self.task_planner.generate_plan(current_desc)
            except Exception as e:
                self.log.warning(f"Failed to get task planner: {e}")
            
            if not subtasks:
                # 如果task_planner为None，使用默认的单任务规划
                subtasks = [{"node_id": routing_result, "description": current_desc, "intent_params": {}}]
            
            # --- 流程 ⑦ & ⑧：创建聚合器 Actor ---
            # 这里不要自己循环发送，而是创建一个临时的 Aggregator Actor 来管理这一组子任务
            # 这样 AgentActor 不会被阻塞，保持无状态
            from capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor
            aggregator_addr = self.createActor(TaskGroupAggregatorActor)
            
            # 构建 Group Request
            from common.messages import TaskGroupRequest
            group_request = TaskGroupRequest(
                parent_task_id=parent_task_id,
                subtasks=subtasks, # 包含子任务描述
                strategy="optuna" if self._should_optimize() else "standard", # 流程 ⑨ 优化判断
                original_sender=sender # 让聚合器直接回给最初的请求者，或者回给 self
            )
            
            # 发送给聚合器，当前 Agent 任务暂时结束（等待回调）
            self.send(aggregator_addr, group_request)
    
    def _should_optimize(self) -> bool:
        """判断是否需要优化"""
        # 简单实现：默认不需要优化
        return False
    
    def _is_leaf_node(self, agent_id: str) -> bool:
        """
        判断当前Agent是否为叶子节点
        通过TreeManager查询是否有子节点

        Args:
            agent_id: Agent节点ID

        Returns:
            bool: 是否为叶子节点
        """
        from agents.tree.tree_manager import TreeManager
        tree_manager = TreeManager()
        children = tree_manager.get_children(agent_id)
        return len(children) == 0

    def _select_execution_node(self, task_description: str) -> Optional[str]:
        """
        ④ 节点选择 - 使用TaskRouter选择最佳执行节点

        Args:
            task_description: 任务描述

        Returns:
            节点ID或None（表示需要MCP Fallback）
        """
        try:
            # 使用TaskRouter选择最佳节点
            if self.task_router:
                routing_result = self.task_router.select_best_actor(task_description, context={})
                if routing_result:
                    return routing_result.get("actor_id") or routing_result
            return None
        except Exception as e:
            self.log.warning(f"Node selection failed: {e}")
            return None

    def _plan_task_execution(self, task_description: str) -> Dict[str, Any]:
        """
        ⑤ 任务规划 - 使用TaskPlanner生成执行计划

        Args:
            task_description: 任务描述

        Returns:
            执行计划，包含subtasks, dependencies, parallel_groups
        """
        try:
            if self.task_planner:
                # 使用TaskPlanner生成计划
                subtasks = self.task_planner.generate_plan(task_description)
                if subtasks:
                    return {
                        "subtasks": subtasks,
                        "dependencies": [],
                        "parallel_groups": []
                    }
        except Exception as e:
            self.log.warning(f"Task planning failed: {e}")

        # Fallback: 返回None，让调用者创建简单计划
        return None

    def _should_execute_in_parallel(self, subtasks: List[Dict[str, Any]]) -> bool:
        """
        ⑥ 并行判断 - 判断子任务是否值得并行执行

        判断标准:
        - 由LLM判断，通过能力来引用
        - 如果子任务之间没有依赖关系且数量较多，考虑并行

        Args:
            subtasks: 子任务列表

        Returns:
            是否应该并行执行
        """
        # 简单策略：如果子任务数量大于1且小于等于5，可以考虑并行
        if len(subtasks) <= 1:
            return False

        # TODO: 这里应该使用LLM来判断，暂时使用简单策略
        # 如果子任务数量在2-5之间，默认不并行（除非明确标记）
        return False

    def _build_task_group_request(self, plan: Dict[str, Any], parent_task_id: str,
                                  should_parallel: bool) -> Dict[str, Any]:
        """
        ⑦ 构建TaskGroupRequest

        Args:
            plan: 任务计划
            parent_task_id: 父任务ID
            should_parallel: 是否并行执行

        Returns:
            TaskGroupRequest消息
        """
        from common.messages.task_messages import TaskSpec

        subtasks = plan.get("subtasks", [])

        # 构建TaskSpec列表
        task_specs = []
        for i, subtask in enumerate(subtasks):
            task_spec = TaskSpec(
                task_id=f"{parent_task_id}.subtask_{i}",
                type=subtask.get("node_id", "mcp"),  # 能力类型
                parameters={
                    "description": subtask.get("description", ""),
                    "context": subtask.get("context", {})
                },
                repeat_count=1,
                aggregation_strategy="single"
            )
            task_specs.append(task_spec)

        # 构建请求
        return {
            "message_type": "execute_task_group",
            "parent_task_id": parent_task_id,
            "subtasks": task_specs,
            "execution_mode": "parallel" if should_parallel else "sequential",
            "aggregation_strategy": "map_reduce",
            "reply_to": self.myAddress
        }

    def _send_to_task_group_aggregator(self, task_group_request: Dict[str, Any], sender: ActorAddress):
        """
        ⑧ 发送到TaskGroupAggregatorActor

        Args:
            task_group_request: 任务组请求
            sender: 原始发送者（用于回复）
        """
        from capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor
        from common.messages.task_messages import TaskGroupRequest

        # 创建TaskGroupAggregatorActor
        aggregator = self.createActor(TaskGroupAggregatorActor)

        # 构建标准的TaskGroupRequest
        group_request = TaskGroupRequest(
            source=self.myAddress,
            destination=aggregator,
            group_id=task_group_request["parent_task_id"],
            tasks=task_group_request["subtasks"],
            reply_to=sender  # 回复给原始发送者
        )

        self.log.info(f"Sending task group to aggregator: {task_group_request['parent_task_id']}")
        self.send(aggregator, group_request)

    def _execute_with_mcp_fallback(self, task: Dict[str, Any], sender: ActorAddress):
        """
        使用MCP Fallback执行任务

        Args:
            task: 任务信息
            sender: 发送者
        """
        task_id = task.get("task_id")
        task_description = task.get("content", task.get("description", ""))

        self.log.info(f"Using MCP fallback for task {task_id}")

        # 调用MCP执行
        from capability_actors.mcp_actor import MCPCapabilityActor
        mcp_actor = self.createActor(MCPCapabilityActor)

        mcp_request = {
            "type": "execute_task",
            "task_id": task_id,
            "task_type": "leaf_task",
            "context": {
                "original_task": task_description,
                "capability": "mcp"
            },
            "capabilities": {
                "name": "mcp"
            },
            "reply_to": sender
        }

        self.send(mcp_actor, mcp_request)
    
    def _execute_leaf_logic(self, task: Dict[str, Any], sender: ActorAddress):
        """处理叶子节点执行逻辑"""
        # --- 流程 ⑩：准备单任务执行 ---
        # 不需要 TaskExecutionService，直接找 ExecutionActor
        
        # 获取 ExecutionActor (通常是单例或池化)
        from capability_actors.execution_actor import ExecutionActor
        exec_actor = self.createActor(ExecutionActor)
        
        # 构建执行请求
        exec_request = {
            "type": "execute_task",
            "task_id": task.get("task_id"),
            "content": task.get("description", task.get("content", "")),
            "params": task.get("context", {}), # 此时参数可能还不完整
            "sender": sender # 记录谁发起的
        }
        
        # 发布任务开始事件
        from events.event_bus import event_bus
        from events.event_types import EventType
        event_bus.publish_task_event(
            task_id=task.get("task_id"),
            event_type=EventType.TASK_STARTED.value,
            source="AgentActor",
            agent_id=self.agent_id,
            data={"node_id": self.agent_id, "type": "leaf_execution"}
        )
        
        self.send(exec_actor, exec_request)

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
            self.send(sender, {"error": "缺少任务ID", "task": task})
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
        self.send(sender, {
            "status": "loop_registered",
            "task_id": parent_task_id,
            "interval_sec": loop_interval,
            "reasoning": "循环任务已成功注册"
        })
        return
    
    def _estimate_loop_interval(self, task_desc: str) -> int:
        """
        估算循环任务的执行间隔
        """
        # 这里可以使用LLM来估算，暂时返回默认值
        return 3600  # 默认1小时


    def _llm_classify_task_intent(self, user_input: str, context: str) -> Dict[str, Any]:
        """
        使用 LLM 判断用户对循环任务的意图。
        返回格式：
        {
        "intent_type": "new_task" | "trigger_existing" | "cancel_existing" | "modify_existing" | "pause_existing" | "resume_existing",
        "task_reference": "日报" | "daily_report_001" | ...,
        "new_interval_sec": 7200,  # 仅 modify 时存在
        "reasoning": "..."
        }
        """
        prompt = f"""你是一个智能任务操作系统。请分析用户当前输入是对哪个历史任务的操作，以及操作类型。

            【用户输入】
            {user_input}

            【上下文（含最近任务记录）】
            {context}

            系统支持以下操作：
            1. 创建新任务（如“帮我查一下天气”）
            2. 对已有任务追加评论（如“刚才那个报告太简略了”、“漏了第三点”）
            3. 修订任务结果（如“把‘成功’改成‘部分成功’”、“更新数据为100”）
            4. 重新执行任务（如“再试一次”、“重新跑一下”）
            5. 取消任务（如“不用做了”）
            6. 归档任务（如“这个可以关了”）
            7. 循环任务专用操作：立即触发、修改间隔、暂停、恢复等

            请输出严格 JSON：
            {{
            "intent_type": "...",
            "target_task_reference": "自然语言描述或ID，如'刚才的天气查询'、'task_20251126_001'",
            "revision_content": "仅 revise_result 时存在，新内容",
            "comment_text": "仅 comment_on_task 时存在",
            "reasoning": "..."
            }}

            intent_type 必须是以下之一：
            {', '.join(TASK_INTENTS)}
            """

        try:
            from capabilities.llm.qwen_adapter import QwenAdapter
            llm = QwenAdapter()
            response = llm.generate(prompt, parse_json=True, max_tokens=500, temperature=0.2)
            
            # 安全转换
            return {
                "intent_type": response.get("intent_type", "new_task"),
                "task_reference": response.get("target_task_reference", ""),
                "new_interval_sec": response.get("new_interval_sec"),
                "reasoning": response.get("reasoning", "")
            }
        except Exception as e:
            self.log.warning(f"Intent classification failed: {e}. Falling back to new_task.")
            return {"intent_type": "new_task", "task_reference": "", "new_interval_sec": None, "reasoning": str(e)}

    def _resolve_task_id_by_reference(self, reference: str) -> Optional[str]:
        """根据用户描述（如“日报”）匹配已注册的循环任务ID"""
        # 使用task_registry根据引用查找任务
        task = self.task_registry.find_task_by_reference(self.current_user_id, reference)
        return task.task_id if task else None


    def _handle_trigger_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            self.send(sender, {"error": "未找到相关循环任务", "reference": ref})
            return

        # 向 LoopScheduler 发送“立即执行”消息（自定义类型）
        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "trigger_task_now",
            "task_id": task_id
        })
        self.send(sender, {"status": "triggered", "task_id": task_id})

    def _handle_cancel_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            self.send(sender, {"error": "未找到相关循环任务"})
            return

        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "cancel_loop_task",
            "task_id": task_id
        })
        self.send(sender, {"status": "cancelled", "task_id": task_id})

    def _handle_modify_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        new_interval = intent.get("new_interval_sec")
        if not new_interval or new_interval <= 0:
            # 让 LLM 估算
            new_interval = self._estimate_loop_interval(intent.get("reasoning", ref))

        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            self.send(sender, {"error": "未找到相关循环任务"})
            return

        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "update_loop_interval",
            "task_id": task_id,
            "interval_sec": int(new_interval)
        })
        self.send(sender, {"status": "updated", "task_id": task_id, "new_interval_sec": new_interval})



    def _handle_pause_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        task_id = self._resolve_task_id_by_reference(intent["task_reference"])
        if task_id:
            self._send_to_scheduler({"type": "pause_loop_task", "task_id": task_id}, sender)
        else:
            self.send(sender, {"error": "任务未找到"})

    def _handle_resume_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        task_id = self._resolve_task_id_by_reference(intent["task_reference"])
        if task_id:
            self._send_to_scheduler({"type": "resume_loop_task", "task_id": task_id}, sender)
        else:
            self.send(sender, {"error": "任务未找到"})

    def _handle_add_comment(self, task: dict, comment: str, sender: ActorAddress):
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            self.send(sender, {"error": "缺少任务ID", "task": task})
            return
        
        # 使用task_registry添加评论
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            self.send(sender, {"error": "未找到相关任务", "task_id": task_id})
            return
        
        # 添加评论
        target_task.comments.append({"content": comment, "created_at": datetime.now().isoformat()})
        self.task_registry.update_task(task_id, {"comments": target_task.comments})
        self.send(sender, {"status": "comment_added", "task_id": task_id})

    def _handle_revise_result(self, task: dict, new_content: str, sender: ActorAddress):
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            self.send(sender, {"error": "缺少任务ID", "task": task})
            return
        
        # 使用task_registry修改结果
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            self.send(sender, {"error": "未找到相关任务", "task_id": task_id})
            return
        
        # 简单策略：全量替换；高级策略：结构化 patch
        self.task_registry.update_task(task_id, {"corrected_result": new_content})
        self.send(sender, {"status": "result_revised", "task_id": task_id})

    def _handle_re_run_task(self, task: dict, sender: ActorAddress):
        # 重新提交原任务描述
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            self.send(sender, {"error": "缺少任务ID", "task": task})
            return
        
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            self.send(sender, {"error": "未找到相关任务", "task_id": task_id})
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
            self.send(sender, {"error": "缺少任务ID", "task": task})
            return
        
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            self.send(sender, {"error": "未找到相关任务", "task_id": task_id})
            return
        
        if target_task.type == TaskType.LOOP:
            self._forward_to_loop_scheduler({"type": "cancel_loop_task", "task_id": task_id}, sender)
        else:
            # 普通任务：标记为 cancelled（若还在运行，可发取消信号）
            self.task_registry.update_task(task_id, {"status": "cancelled"})
            self.send(sender, {"status": "task_cancelled", "task_id": task_id})
    
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
        self.send(sender, {"status": "command_sent", "task_id": task_id, "command": forward_msg["type"]})


    def _resolve_target_task(self, reference: str) -> Optional[Dict[str, Any]]:
        """
        返回匹配的任务元数据，包含：
        - task_id
        - type: "loop" | "one_time"
        - status: "completed" | "failed" | "running" | "cancelled"
        - result: {...}
        - created_at: timestamp
        """
        # 策略1：精确匹配 task_id
        if reference.startswith("task_") or "_" in reference:
            task = self.manager.get_task_by_id(reference)
            if task:
                return task

        # 策略2：语义匹配（用嵌入或关键词）
        recent_tasks = self.manager.get_recent_tasks(limit=10)  # 从记忆或任务库获取
        
        # 简化版：关键词匹配
        ref_lower = reference.lower()
        for task in recent_tasks:
            desc = (task.get("description") or "").lower()
            result = str(task.get("result", "")).lower()
            if ref_lower in desc or ref_lower in result:
                return task

        # 策略3：默认指向最新任务（“刚才那个”）
        if "刚才" in reference or "上一个" in reference or "那个" in reference:
            return recent_tasks[0] if recent_tasks else None

        return None
   
   
    def _send_to_scheduler(self, msg: dict, reply_to: ActorAddress):
        scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(scheduler, msg)
        # 可选：等待响应或直接回复
        self.send(reply_to, {"status": "command_sent", **msg})

    def _handle_execution_message(self, msg: Dict[str, Any], sender: ActorAddress):
        """统一处理 SubtaskResult / SubtaskError"""
        task_id = msg.get("task_id")
        if not task_id or "." not in task_id:
            return
        parent_id = task_id.split(".")[0]
        state = self._aggregation_state.get(parent_id)
        if not state:
            return

        if isinstance(msg, dict) and "error" in msg:
            self._handle_execution_error(msg, sender)
        else:
            self._handle_execution_result(msg, sender)

    def _handle_execution_result(self, result_msg: Dict[str, Any], sender: ActorAddress):
        """处理执行结果"""
        task_id = result_msg.get("task_id")
        result_data = result_msg.get("result", {})
        status = result_data.get("status", "SUCCESS")

        if status == "SUCCESS":
            # 1. 写入记忆
            if self.memory_cap:
                self.memory_cap.add_memory_intelligently(f"Task completed: {task_id}")

            # 2. 检查是否需要发送优化反馈
            self._send_optimization_feedback(task_id, result_msg, success=True)

            # 3. 如果这是父任务的子任务，检查是否聚合完成
            if self.current_aggregator:
                # 通知聚合器
                self.send(self.current_aggregator, result_msg)
            else:
                # 4. 如果是根任务，直接返回给前台InteractionActor
                original_sender = self.task_id_to_sender.get(task_id, sender)

                # 构建给前台的消息
                response_to_frontend = {
                    "message_type": "task_completed",
                    "task_id": task_id,
                    "result": result_data,
                    "message": "任务执行完成"
                }

                self.send(original_sender, response_to_frontend)

                # 5. 发布事件
                from events.event_bus import event_bus
                from events.event_types import EventType
                event_bus.publish_task_event(
                    task_id=task_id,
                    event_type=EventType.TASK_COMPLETED.value,
                    source="AgentActor",
                    agent_id=self.agent_id,
                    data={"result": result_data}
                )

                # 清理映射
                if task_id in self.task_id_to_sender:
                    del self.task_id_to_sender[task_id]
                # 清理ExecutionActor地址映射
                if task_id in self.task_id_to_execution_actor:
                    del self.task_id_to_execution_actor[task_id]

        elif status == "FAILED":
            # 发送优化反馈（失败情况）
            self._send_optimization_feedback(task_id, result_msg, success=False)

            # 触发 MCP Fallback 机制 (Step ⑤ 的 fallback)
            self._trigger_fallback(task_id, result_data.get("error_msg", "执行失败"))

    def _send_optimization_feedback(self, task_id: str, result_msg: Dict[str, Any], success: bool):
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

            result_data = result_msg.get("result", {})

            execution_record = {
                "execution_time": datetime.now().isoformat(),
                "parameters": result_msg.get("parameters", {}),
                "result": result_data,
                "success": success,
                "duration": result_data.get("duration", 0.0),
                "score": self._calculate_execution_score(result_data, success),
                "error": result_data.get("error") if not success else None
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

    def _calculate_execution_score(self, result_data: Dict[str, Any], success: bool) -> float:
        """
        计算执行分数

        Args:
            result_data: 执行结果数据
            success: 是否成功

        Returns:
            0.0-1.0之间的分数
        """
        if not success:
            return 0.0

        # 基础分数
        base_score = 0.7

        # 根据执行时间调整
        duration = result_data.get("duration", 0.0)
        if duration < 1.0:
            base_score += 0.2
        elif duration > 10.0:
            base_score -= 0.2

        # 根据结果质量调整（如果有）
        quality_score = result_data.get("quality_score")
        if quality_score is not None:
            base_score = (base_score + quality_score) / 2

        # 确保在0-1范围内
        return max(0.0, min(1.0, base_score))
    
    def _format_response(self, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化响应"""
        return {
            "status": "completed",
            "result": result_data,
            "message": "任务执行完成"
        }
    
    def _trigger_fallback(self, task_id: str, error_msg: str):
        """触发MCP Fallback机制"""
        from capability_actors.mcp_actor import MCPCapabilityActor
        mcp_actor = self.createActor(MCPCapabilityActor)
        self.send(mcp_actor, {
            "type": "fallback_request",
            "task_id": task_id,
            "error_msg": error_msg
        })

    def _handle_execution_error(self, error_msg: Dict[str, Any], sender: ActorAddress):
        task_id = error_msg.get("task_id")
        if not task_id or "." not in task_id:
            return
        parent_id = task_id.split(".")[0]
        state = self._aggregation_state.get(parent_id)
        if state:
            state["pending"].discard(task_id)
            # 可选：立即失败或继续等待其他子任务

    def _finalize_aggregation(self, parent_task_id: str, state: Dict[str, Any]):
        sender = state["sender"]
        final_result = {
            "status": "completed",
            "subtask_results": state["results"]
        }
        
        # 发送任务完成事件
        event_bus.publish_task_event(
            task_id=parent_task_id,
            event_type=EventType.TASK_COMPLETED.value,
            source="AgentActor",
            agent_id=self.agent_id,
            data={
                "result": final_result,
                "completed_tasks": len(state["results"])
            }
        )
        
        self.send(sender, SubtaskResult(task_id=parent_task_id, result=final_result))
        if self.memory_cap:
            self.memory_cap.add_memory_intelligently(f"Task completed: {parent_task_id}")

    # ======================
    # 私有辅助方法（按职责拆分）
    # ======================

    def _ensure_memory_ready(self) -> bool:
        if self.memory_cap is None:
            self.log.error("Memory capability not ready")
            return False
        return True

    def _plan_subtasks(self, node_id: str, goal: str) -> List[Dict[str, Any]]:
        """
        使用TaskPlanner进行任务规划
        """
        # 获取任务规划能力
        planner = capability_registry.get_capability("planning")
        if planner:
            try:
                # 使用实际的TaskPlanner进行规划
                return planner.plan_subtasks(node_id, {
                    "main_intent": goal,
                    "execution_memory": {}
                })
            except Exception as e:
                self.log.error(f"Task planning failed: {e}")
        
        # 回退到简单实现
        return [{
            "node_id": node_id,
            "description": goal,
            "intent_params": {}
        }]

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

    def _create_child_actor(self, capability: str) -> Optional[ActorAddress]:
        try:
            actor_cls = self._capability_to_actor_class(capability)
            return self.createActor(actor_cls, globalName=capability)
        except Exception as e:
            self.log.error(f"Failed to create child actor for {capability}: {e}")
            return None

    def _dispatch_to_fallback(self, task_id: str, context: str, sender: ActorAddress):
        # 导入McpLlmActor
        from capability_actors.mcp_actor import MCPCapabilityActor
        fallback_addr = self.createActor(MCPCapabilityActor)
        self.send(fallback_addr, McpFallbackRequest(task_id=task_id, context=context))
        self._aggregation_state[task_id] = {
            "pending": {"MCP_FALLBACK_TASK"},
            "results": {},
            "sender": sender
        }

    def _capability_to_actor_class(self, capability: str):
        """
        根据能力名称映射到对应的Actor类
        注意：这里使用了硬编码的映射关系，实际项目中应该从配置或注册表中获取
        """
        from capability_actors.data_actor import DataCapabilityActor
        from capability_actors.mcp_actor import MCPCapabilityActor
        from capability_actors.memory_actor import MemoryCapabilityActor
        from capability_actors.dify_actor import DifyCapabilityActor
        
        actor_map = {
            "data": DataCapabilityActor,
            "mcp": MCPCapabilityActor,
            "memory": MemoryCapabilityActor,
            "dify": DifyCapabilityActor
        }
        
        actor_cls = actor_map.get(capability)
        if not actor_cls:
            # 默认使用MCP能力Actor
            return MCPCapabilityActor
        return actor_cls

    def _llm_decide_task_strategy(self, task_desc: str, context: str) -> Dict[str, Any]:

        """
        使用 Qwen 判断任务策略：
        - 是否为循环任务（如每日报告）
        - 是否应并行执行（如生成多个创意方案）

        返回 dict 包含:
          is_loop: bool
          is_parallel: bool
          reasoning: str (LLM 的思考过程)
        """
        prompt = f"""你是一个智能任务分析器。请根据以下信息判断任务的两个属性：

                【当前任务描述】
                {task_desc}

                【相关记忆与上下文】
                {context}

                请严格按以下 JSON 格式输出，不要包含任何额外内容：
                {{
                "is_loop": false,
                "is_parallel": false,
                "reasoning": "简要说明判断依据"
                }}
                """

        try:
            # 使用新的能力获取方式获取LLM能力
            llm = get_capability("qwen", expected_type=ILLMCapability)
            result = llm.generate(prompt, parse_json=True, max_tokens=300)

            # 确保字段存在且类型正确
            return {
                "is_loop": bool(result.get("is_loop", False)),
                "is_parallel": bool(result.get("is_parallel", False)),
                "reasoning": str(result.get("reasoning", "No reasoning provided."))
            }

        except Exception as e:
            self.log.error(f"Error in _llm_decide_task_strategy: {e}")
            # 安全回退
            return {
                "is_loop": False,
                "is_parallel": False,
                "reasoning": f"Failed to analyze due to error: {str(e)}. Using default strategy."
            }


    def _report_event(self, event_type: str, task_id: str, details: Dict[str, Any]):
        self.log.info(f"[{event_type}] {task_id}: {details}")

    def _report_error(self, task_id: str, error: str, sender: ActorAddress):
        self.send(sender, SubtaskError(task_id=task_id, error=error))

    def _execute_as_leaf(self, task: Dict[str, Any], task_id: str, sender: ActorAddress):
        result = {"status": "executed_by_parent", "output": "Leaf execution stub"}
        self.send(sender, SubtaskResult(task_id=task_id, result=result))