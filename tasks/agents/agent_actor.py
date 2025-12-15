import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from thespian.actors import Actor, ActorAddress, ActorExitRequest,ChildActorExited
import uuid
from ..common.messages.agent_messages import (
    AgentTaskMessage, ResumeTaskMessage, 
)
from ..common.messages.types import MessageType
from ..common.messages.task_messages import TaskCompletedMessage
from ..common.messages.interact_messages import TaskResultMessage, TaskPausedMessage as InteractTaskPausedMessage

# 导入新的能力管理模块
from ..capabilities import init_capabilities, get_capability, get_capability_registry

# 导入能力接口
from ..capabilities.llm_memory.interface import IMemoryCapability


# 导入新的能力接口
from ..capabilities.task_planning.interface import ITaskPlanningCapability

# 导入事件总线
from ..events.event_bus import event_bus


logger = logging.getLogger(__name__)


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
        """
        接收并处理消息
        """
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
        """
        从任务消息中初始化AgentActor
        """
        self.agent_id = msg.agent_id
        if msg.task_path:
            self._task_path: Optional[str] = msg.task_path  
        else:
            self._task_path = ""

        from .tree.tree_manager import TreeManager
        tree_manager = TreeManager()
        self.meta=tree_manager.get_agent_meta(self.agent_id)
        try:
            # 使用新的能力获取方式
            self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
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
            # 简化：移除其他创建类型的处理，只保留核心的NEW_TASK

        elif category == TaskOperationCategory.EXECUTION:
            # 执行控制类 → 执行对应操作
            if operation_type == TaskOperationType.EXECUTE_TASK:
                # 立即执行任务
                self._handle_task_creation(task.__dict__, sender)
            elif operation_type == TaskOperationType.RESUME_TASK:
                # 恢复任务
                self._resume_paused_task(parent_task_id, operation_result.get("parameters", {}), sender)

        else:
            # 未知类型或其他类型，暂时不处理
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

        # 发布任务创建事件
        event_bus.publish_task_event(
            task_id=parent_task_id,
            event_type=EventType.TASK_CREATED.value,
            source="AgentActor",
            agent_id=self.agent_id,
            data={
                "user_input": user_input[:100],
                "user_id": self.current_user_id
            }
        )

        decision_context = self.memory_cap.build_conversation_context(self.current_user_id)
        # --- 流程 ⑤: 任务规划 ---
        event_bus.publish_task_event(
            task_id=parent_task_id,
            event_type=EventType.TASK_PLANNING.value,
            source="AgentActor",
            agent_id=self.agent_id,
            data={"message": "开始任务规划"}
        )
        
        plans = self._plan_task_execution(user_input, decision_context)  
        if plans:
            for plan in plans:
                # 仅对 AGENT 类型的节点进行判断，MCP 通常是确定性工具
                if plan.get('type') == 'AGENT':
                    # 简化：直接使用默认策略，不调用LLM判断
                    plan['is_parallel'] = False
                    plan['strategy_reasoning'] = "Default strategy: sequential execution"
                else:
                    # MCP 默认单次执行
                    plan['is_parallel'] = False      

            # --- 流程 ⑦: 构建TaskGroupRequest ---
            task_group_request = self._build_task_group_request(plans, parent_task_id, user_input)

            # --- 流程 ⑧: 发送给TaskGroupAggregatorActor ---
            self._send_to_task_group_aggregator(task_group_request, sender)
            
            # 发布任务分发事件
            event_bus.publish_task_event(
                task_id=parent_task_id,
                event_type=EventType.TASK_DISPATCHED.value,
                source="AgentActor",
                agent_id=self.agent_id,
                data={
                    "plans_count": len(plans),
                    "message": "任务已分发给子Agent"
                }
            )

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
            task_op_cap: ITaskOperationCapability = get_capability("task_operation", expected_type=ITaskOperationCapability)

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

    def _plan_task_execution(self, task_description: str, memory_context: str = None) -> Dict[str, Any]:
        """
        ⑤ 任务规划 - 使用TaskPlanner生成执行计划

        Args:
            task_description: 任务描述
            memory_context: 记忆上下文

        Returns:
            执行计划，包含subtasks, dependencies, parallel_groups
        """
        try:
            if not self.task_planner:
                self.task_planner: ITaskPlanningCapability = get_capability("task_planning", expected_type=ITaskPlanningCapability)
            
            # 使用TaskPlanner生成计划
            subtasks = self.task_planner.generate_execution_plan(self.agent_id, task_description, memory_context)
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
        """
        构建任务组请求
        """
        from ..common.messages.task_messages import TaskSpec, TaskGroupRequestMessage

        task_specs = []
        for task in tasks:
            # 防御性处理：确保必要字段存在
            task_clean = {
                "step": int(task.get("step", 0)),
                "type": task.get("type", "unknown"),
                "executor": task.get("executor", "unknown"),
                "description": task.get("description", ""),
                "params": str(task.get("params", "")),
                "is_parallel": bool(task.get("is_parallel", False)),
                "strategy_reasoning": task.get("strategy_reasoning", ""),
                "is_dependency_expanded": bool(task.get("is_dependency_expanded", False)),
                "original_parent": task.get("original_parent"),
                "user_id": self.current_user_id,
            }

            # 如果你希望保留原始 task 中的其他字段到 extras
            extra_keys = set(task.keys()) - set(task_clean.keys())
            if extra_keys:
                task_clean.update({k: task[k] for k in extra_keys})

            task_spec = TaskSpec(**task_clean)
            task_specs.append(task_spec)

        request = TaskGroupRequestMessage(
            task_id=str(uuid.uuid4()),           # ← 唯一任务 ID
            trace_id=str(uuid.uuid4()),          # ← 链路追踪 ID
            task_path=self._task_path + self.agent_id,  # ← 任务路径
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
        from ..capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor

        # 创建TaskGroupAggregatorActor
        aggregator = self.createActor(TaskGroupAggregatorActor)

        group_request = task_group_request

        self.log.info(f"Sending task group to aggregator")
        self.send(aggregator, group_request)

    def _handle_task_result(self, result_msg: TaskCompletedMessage, sender: ActorAddress):
        """
        统一处理任务结果（成功、失败、错误、需要输入），使用TaskCompletedMessage向上报告
        """
        task_id = result_msg.task_id
        result_data = result_msg.result
        status = result_msg.status

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

    def _ensure_memory_ready(self) -> bool:
        """
        确保内存能力已准备就绪
        """
        if self.memory_cap is None:
            self.log.error("Memory capability not ready")
            return False
        return True
    
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
            from ..capabilities.llm.interface import ILLMCapability
            from ..capabilities import get_capability
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
