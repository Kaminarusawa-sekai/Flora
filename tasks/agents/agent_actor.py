import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from thespian.actors import Actor, ActorAddress, ActorExitRequest,ChildActorExited
import uuid
from common.messages import (
    AgentTaskMessage, TaskCompletedMessage, ResumeTaskMessage,
     TaskGroupRequestMessage, 
)
from common.taskspec import TaskSpec
from common.context.context_entry import ContextEntry
# 导入新的能力管理模块
from capabilities import init_capabilities, get_capability, get_capability_registry

# 导入能力接口
from capabilities.llm_memory.interface import IMemoryCapability


# 导入新的能力接口
from capabilities.task_planning.interface import ITaskPlanningCapability

# 导入事件总线和EventType
from events.event_bus import event_bus
from common.event import EventType


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
            # 不再直接处理 paused 消息，改为通过 TaskCompletedMessage 的 NEED_INPUT 状态处理
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
        user_input = task.get_user_input()
        user_id = task.user_id
        task_id = task.task_id
        reply_to = task.reply_to or sender  # 前台要求回复的地址


        if not task_id:
            self.log.error("Missing task_id in agent_task")
            return

        # 记录回复地址和当前用户ID
        self.task_id_to_sender[task_id] = reply_to
        self.current_user_id = user_id

        self.log.info(f"[AgentActor] Handling task {task_id}: {user_input[:50]}...")

        # 发布任务创建事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_CREATED.value,
            trace_id=task.trace_id,
            task_path=self._task_path or "",
            source="AgentActor",
            agent_id=self.agent_id,
            data={
                "user_input": user_input[:100],
                "user_id": self.current_user_id+str(self.agent_id)
            },
            user_id=self.current_user_id
        )


        # 写入记忆（按单节点存储，检索按 scope 聚合）
        try:
            memory_input = task.content or task.description or user_input
            node_scope = self._build_node_memory_scope(self.current_user_id, task.task_path)
            root_scope = self._build_memory_scope(self.current_user_id, task.task_path)
            metadata = {
                "root_scope": root_scope,
                "agent_id": self.agent_id,
                "task_path": task.task_path
            }
            self.memory_cap.add_memory_intelligently(node_scope, memory_input, metadata)
        except Exception as e:
            self.log.warning(f"Memory write skipped: {e}")



        # 构建对话上下文
        conversation_context = self.memory_cap.build_conversation_context(
            self._build_memory_scope(self.current_user_id, task.task_path),
            task.content or ""
        )
        
        # --- 流程 ⑤: 任务规划 ---
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_PLANNING.value,
            trace_id=task.trace_id,
            task_path=self._task_path or "",
            source="AgentActor",
            agent_id=self.agent_id,
            data={
                "message": "开始任务规划"
            },
            user_id=self.current_user_id
        )
        
        # 生成执行计划
        plans = self._plan_task_execution(user_input, conversation_context)  
        if plans:
            for plan in plans:
                # 仅对 AGENT 类型的节点进行判断，MCP 通常是确定性工具
                if plan.get('type') == 'AGENT':
                    self._llm_decide_should_execute_in_parallel(plan, conversation_context)
                else:
                    # MCP 默认单次执行
                    plan['is_parallel'] = False      

            logger.info(f"[AgentActor] Task planning result:\n{plans}")
            # --- 流程 ⑦: 构建TaskGroupRequest ---
            task_group_request = self._build_task_group_request(plans, task)

            # --- 流程 ⑧: 发送给TaskGroupAggregatorActor ---
            self._send_to_task_group_aggregator(task_group_request, reply_to)
            
            # 发布任务分发事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.TASK_DISPATCHED.value,
                trace_id=task.trace_id,
                task_path=self._task_path or "",
                source="AgentActor",
                agent_id=self.agent_id,
                data={
                    "plans": plans,
                    "message": "任务已分发给子Agent"
                },
                user_id=self.current_user_id
            )


    def _handle_resume_task(self, message: ResumeTaskMessage, sender: ActorAddress):
        """
        处理来自前台的resume_task消息并执行恢复任务链

        Args:
            message: 包含task_id, parameters, user_id, reply_to, trace_id等
            sender: 发送者
        """
        # 从ResumeTaskMessage中提取所有参数（ResumeTaskMessage继承自TaskMessage，拥有trace_id等字段）
        task_id = message.task_id
        parameters = message.parameters
        user_id = message.user_id
        reply_to = message.reply_to or sender
        trace_id = message.trace_id  # 使用ResumeTaskMessage的trace_id
        task_path = message.task_path  # 使用ResumeTaskMessage的task_path
        
        # 更新当前用户ID
        if user_id:
            self.current_user_id = user_id
        
        self.log.info(f"Received resume task request for {task_id} from InteractionActor, trace_id: {trace_id}, task_path: {task_path}")

        # 记录reply_to以便回复前台
        self.task_id_to_sender[task_id] = reply_to

        # 发布任务恢复事件，使用ResumeTaskMessage的参数
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_RESUMED.value,
            trace_id=trace_id,  # 使用ResumeTaskMessage的trace_id
            task_path=task_path,  # 使用ResumeTaskMessage的task_path
            source="AgentActor",
            agent_id=self.agent_id,
            data={
                "parameters": list(parameters.keys()),
                "user_id": self.current_user_id
            },
            user_id=self.current_user_id
        )

        # 关键：从映射中获取原来的ExecutionActor地址
        exec_actor = self.task_id_to_execution_actor.get(task_id)

        if not exec_actor:
            self.log.error(f"Cannot find ExecutionActor for task {task_id}, task cannot be resumed")
            # 通知前台恢复失败，使用ResumeTaskMessage的参数
            task_result = TaskCompletedMessage(
                task_id=task_id,
                trace_id=trace_id,
                task_path=task_path,
                result={"error": "Cannot find the ExecutionActor for this task"},
                status="ERROR",
                step=0
            )
            self.send(reply_to, task_result)
            return

        # 构建恢复消息，发送到原来的ExecutionActor，使用ResumeTaskMessage的参数
        exec_request = {
            "type": "resume_execution",
            "task_id": task_id,
            "trace_id": trace_id,  # 使用ResumeTaskMessage的trace_id
            "task_path": task_path,  # 使用ResumeTaskMessage的task_path
            "parameters": parameters,
            "reply_to": self.myAddress,
            "user_id": self.current_user_id
        }

        self.log.info(f"Sending resume request to original ExecutionActor for task {task_id}, trace_id: {trace_id}")
        self.send(exec_actor, exec_request)

        # 记录sender以便接收结果（更新，因为可能是新的前台请求）
        self.task_id_to_sender[task_id] = reply_to
    @staticmethod
    def _extract_root_agent_id(task_path: Optional[str]) -> str:
        if not task_path:
            return ""
        parts = [part for part in task_path.split("/") if part]
        return parts[0] if parts else ""

    def _build_memory_scope(self, user_id: Optional[str], task_path: Optional[str]) -> str:
        if not user_id:
            return ""
        root_agent_id = self._extract_root_agent_id(task_path) or self.agent_id
        if root_agent_id:
            return f"{user_id}:{root_agent_id}"
        return user_id

    def _build_node_memory_scope(self, user_id: Optional[str], task_path: Optional[str]) -> str:
        if not user_id:
            return ""
        root_agent_id = self._extract_root_agent_id(task_path) or self.agent_id
        if root_agent_id:
            return f"{user_id}:{root_agent_id}:{self.agent_id}"
        return f"{user_id}:{self.agent_id}"
   

    def _handle_task_paused_from_execution(self, message: Any, sender: ActorAddress):
        """
        处理来自ExecutionActor的NEED_INPUT状态，使用TaskCompletedMessage向上报告

        Args:
            message: 包含task_id, missing_params, question, execution_actor_address
            sender: ExecutionActor的地址
        """
        task_id = message.task_id
        missing_params = getattr(message, "missing_params", None)
        question = getattr(message, "question", "")
        if not missing_params:
            result_payload = getattr(message, "result", None)
            if isinstance(result_payload, dict):
                missing_params = result_payload.get("missing_params")
                if not missing_params and isinstance(result_payload.get("step_result"), dict):
                    missing_params = result_payload["step_result"].get("missing_params")
                if not question:
                    question = result_payload.get("question") or result_payload.get("message", "")
        if missing_params is None:
            missing_params = []
        execution_actor_address = getattr(message, "execution_actor_address", None)

        self.log.info(f"Task {task_id} needs input by ExecutionActor, forwarding with TaskCompletedMessage")

        # 重要：保存ExecutionActor地址到映射，以便恢复时能找到
        if execution_actor_address:
            self.task_id_to_execution_actor[task_id] = execution_actor_address
            self.log.info(f"Saved ExecutionActor address for task {task_id}")
        else:
            self.log.warning(f"No execution_actor_address in need_input message for task {task_id}")

        # 从传入的message中获取trace_id和task_path，如果没有则使用默认值
        trace_id = getattr(message, "trace_id", None) or task_id
        task_path = getattr(message, "task_path", None) or self._task_path or ""

        # 构建TaskCompletedMessage，直接返回给调用者
        task_result = TaskCompletedMessage(
            task_id=task_id,
            trace_id=trace_id,
            task_path=task_path,
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
                # 直接发送TaskCompletedMessage，不再使用InteractTaskPausedMessage
                self.send(original_sender, task_result)
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
        plans: List[Dict[str, Any]],
        task: AgentTaskMessage
    ) -> TaskGroupRequestMessage:
        """
        构建任务组请求
        """
        task_specs = []
        for plan in plans:
            # 防御性处理：确保必要字段存在
            task_clean = {
                "step": int(plan.get("step", 0)),
                "type": plan.get("type", "unknown"),
                "executor": plan.get("executor", "unknown"),
                "description": plan.get("description", ""),
                "content": plan.get("content", ""),  # ← 现在用 content 替代 params
                "is_parallel": bool(plan.get("is_parallel", False)),
                "strategy_reasoning": plan.get("strategy_reasoning", ""),
                "is_dependency_expanded": bool(plan.get("is_dependency_expanded", False)),
                "original_parent": plan.get("original_parent"),
                "user_id": getattr(self, 'current_user_id', task.user_id),  # 优先用 self.current_user_id
                "task_id": str(uuid.uuid4()),
            }

            # 允许 plan 中包含额外字段（因 TaskSpec.Config.extra='allow'）
            known_keys = set(task_clean.keys())
            extra_keys = set(plan.keys()) - known_keys
            for k in extra_keys:
                task_clean[k] = plan[k]

            task_spec = TaskSpec(**task_clean)
            task_specs.append(task_spec)

        # 构建完整的 TaskGroupRequestMessage
        request = TaskGroupRequestMessage(
            task_id=task.task_id,
            trace_id=task.trace_id,
            task_path=task.add_task_path(self.agent_id),
            content=task.content,               # 父任务内容
            description=task.description,       # 父任务描述
            global_context=task.global_context.copy(),
            enriched_context=task.enriched_context.copy(),
            user_id=getattr(self, 'current_user_id', task.user_id),
            reply_to=task.reply_to,
            subtasks=task_specs,
            strategy="standard",  # 可根据需要从 task 或 plans 中提取策略
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

        if status=="NEED_INPUT":
            self._handle_task_paused_from_execution(result_msg, sender)
            return

        if self.current_aggregator:
            # 2. 如果有聚合器，通知聚合器
            self.send(self.current_aggregator, result_msg)
        else:
            # 3. 如果是根任务，直接返回给前台InteractionActor
            original_sender = self.task_id_to_sender.get(task_id, sender)

            # 构建前台交互消息，使用TaskCompletedMessage代替TaskResultMessage
            error_str = None
            if isinstance(result_data, dict) and "error" in result_data:
                error_str = str(result_data["error"])
            elif hasattr(result_msg, "error") and result_msg.error:
                error_str = str(result_msg.error)
            
            # 构建TaskCompletedMessage，使用SUCCESS或FAILED状态
            task_result = TaskCompletedMessage(
                task_id=task_id,
                trace_id=result_msg.trace_id,
                task_path=result_msg.task_path,
                result=result_data,
                status=status,  # 使用传入的status，可能是SUCCESS、FAILED、NEED_INPUT等
                error=error_str,
                step=0  # 步骤号，根据实际情况调整
            )

            self.send(original_sender, task_result)

            # 4. 发布事件
            event_type = EventType.TASK_COMPLETED.value if status == "SUCCESS" else EventType.TASK_FAILED.value
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=event_type,
                trace_id=result_msg.trace_id or task_id,  # 使用result_msg.trace_id或task_id作为trace_id
                task_path=self._task_path or "",
                source="AgentActor",
                agent_id=self.agent_id,
                data={"result": result_data},
                user_id=self.current_user_id,
                error=error_str
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
