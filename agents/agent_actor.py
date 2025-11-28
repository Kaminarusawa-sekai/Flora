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

# 导入新的能力接口
from capabilities.cognition.intent_router import IIntentRouterCapability
from capabilities.context.conversation_manager import IConversationManagerCapability
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


class AgentActor(Actor):
    def __init__(self):
        super().__init__()
        self.agent_id: str = ""
        self.memory_cap: Optional[IMemoryCapability] = None
        
        self._aggregation_state: Dict[str, Dict] = {}
        self.task_id_to_sender: Dict[str, ActorAddress] = {}
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
        """主任务处理入口：协调路由 → 规划 → 分发"""
        if not self._ensure_memory_ready():
            return
        
        # 获取用户输入和用户ID
        user_input = task.get("content", task.get("description", ""))
        user_id = task.get("user_id", "default_user")
        parent_task_id = task.get("task_id")
        
        if not parent_task_id:
            self.log.error("Missing task_id in agent_task")
            return
            
        self.task_id_to_sender[parent_task_id] = sender
        self.current_user_id = user_id
        
        # --- 流程 ①：草稿判断 ---
        # 使用新的对话管理能力
        draft_response = self.conversation_manager.process_user_input(user_input, user_id)
        
        # 检查是否需要继续处理（如果是恢复草稿，直接返回响应）
        if "继续刚才的任务" in draft_response:
            self.send(sender, {
                "status": "draft_restored",
                "message": draft_response
            })
            return
        
        # --- 流程 ②：意图判断 ---
        # 使用新的意图识别能力
        intent_result = self.intent_router.classify_intent(user_input)
        
        if intent_result.intent == IntentType.AMBIGUOUS:
            # 处理澄清逻辑
            self.send(sender, {
                "status": "need_clarification",
                "message": "我不太确定你的意思，你能再详细说明一下吗？"
            })
            return
        
        # --- 流程 ③：任务操作判断 ---
        operation = self._llm_classify_task_operation(user_input, intent)
        
        if operation == "LOOP_TASK":
            # 转入流程 ④ 循环任务处理
            self._handle_loop_task_setup(task, sender)
        elif operation == "NEW_TASK":
            # 转入流程 ⑤ 新任务执行
            self._handle_new_task_execution(task, sender)
        elif operation in ["comment_on_task", "revise_result", "re_run_task", "cancel_task"]:
            # 处理其他任务操作
            self._handle_task_operation(task, sender, user_input, parent_task_id)
        else:
            # 处理其他意图
            self.send(sender, {
                "status": "not_supported",
                "message": f"当前不支持{operation}类型的请求"
            })
            return
    
    def _handle_task_operation(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str, parent_task_id: str):
        """处理任务相关操作"""
        # 使用LLM判断具体的任务操作
        task_operation = self._llm_classify_task_operation(current_desc)
        operation_type = task_operation.get("operation_type", "new_task")
        
        # 路由到对应处理器
        if operation_type == "new_task":
            self._handle_new_task(task, sender, current_desc, parent_task_id)
        elif operation_type == "comment_on_task":
            self._handle_add_comment(task, task_operation.get("comment_text", ""), sender)
        elif operation_type == "revise_result":
            self._handle_revise_result(task, task_operation.get("revision_content", ""), sender)
        elif operation_type == "re_run_task":
            self._handle_re_run_task(task, sender)
        elif operation_type == "cancel_task":
            self._handle_cancel_any_task(task, sender)
        elif operation_type in ["trigger_existing", "modify_loop_interval", "pause_loop", "resume_loop"]:
            # 转发给循环调度器
            self._forward_to_loop_scheduler(task_operation, task.get("task_id"), sender)
        else:
            self.send(sender, {
                "error": "不支持的操作类型",
                "operation_type": operation_type
            })
    
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
    
    def _llm_classify_task_operation(self, user_input: str, intent: Any = None) -> str:
        """
        使用LLM判断具体的任务操作
        """
        try:
            # 使用新的任务操作分类能力
            task_operation_capability = get_capability("task_operation", expected_type=ITaskOperationCapability)
            return task_operation_capability.classify_task_operation(user_input, intent)
        except Exception as e:
            self.log.warning(f"Task operation classification failed: {e}. Falling back to new_task.")
            return "NEW_TASK"
    
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
            
            # 2. 如果这是父任务的子任务，检查是否聚合完成
            if self.current_aggregator:
                # 通知聚合器
                self.send(self.current_aggregator, result_msg)
            else:
                # 3. 如果是根任务，直接返回给用户 (Step ⑫)
                final_response = self._format_response(result_data)
                # 假设 original_sender 在上下文中保存了
                original_sender = self.task_id_to_sender.get(task_id, sender)
                self.send(original_sender, final_response)
                
                # 4. 发布事件
                from events.event_bus import event_bus
                from events.event_types import EventType
                event_bus.publish_task_event(
                    task_id=task_id,
                    event_type=EventType.TASK_COMPLETED.value,
                    source="AgentActor",
                    agent_id=self.agent_id,
                    data={"result": result_data}
                )
        elif status == "FAILED":
            # 触发 MCP Fallback 机制 (Step ⑤ 的 fallback)
            self._trigger_fallback(task_id, result_data.get("error_msg", "执行失败"))
    
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
        pending = set()
        
        # 获取任务执行服务Actor
        from capability_actors.task_execution_service import TaskExecutionService
        task_execution_addr = self.createActor(TaskExecutionService)
        
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

            # 构造任务执行请求
            task_request = {
                "type": "execute_task",
                "task_id": child_task_id,
                "task_type": "leaf_task",
                "context": final_child_context,
                "capabilities": {
                    "name": child_cap
                }
            }

            # 发送任务到执行服务
            self.send(task_execution_addr, task_request)
            pending.add(child_task_id)

            self._report_event("subtask_spawned", child_task_id, {
                "parent_task_id": parent_task_id,
                "capability": child_cap,
                "child_address": str(task_execution_addr)
            })
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