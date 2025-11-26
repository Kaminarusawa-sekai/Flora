import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from thespian.actors import Actor, ActorAddress

from new.capabilities.llm_memory.memory_capability import MemoryCapability
from new.capability_actors.mcp_actor import MCPCapabilityActor
from new.common.messages import SubtaskResult, SubtaskError, TaskMessage, McpFallbackRequest


from new.capabilities.registry import capability_registry


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
        self.memory_cap: Optional[MemoryCapability] = None
        # self._task_coordinator = TaskCoordinator()
        self.router=router = capability_registry.get_capability("routing")
        
        self._aggregation_state: Dict[str, Dict] = {}
        self.task_id_to_sender: Dict[str, ActorAddress] = {}
        self.log = logging.getLogger("AgentActor")  # 初始日志，后续按 agent_id 覆盖

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
        self.memory_cap = MemoryCapability(user_id=self.agent_id)
        if not self.memory_cap.initialize():
            self.log.error(f"Failed to initialize memory capability for agent {self.agent_id}")
            self.send(sender, {"status": "init_failed", "agent_id": self.agent_id})
            return
        self.log = logging.getLogger(f"AgentActor_{self.agent_id}")
        self.log.info(f"AgentActor initialized for {self.agent_id}")
        self.send(sender, {"status": "initialized", "agent_id": self.agent_id})

    def _handle_task(self, task: Dict[str, Any], sender: ActorAddress):
        """主任务处理入口：协调路由 → 规划 → 分发"""
        if not self._ensure_memory_ready():
            return
        
        ##TODO：加入来自于mutifeature的人格记忆
        parent_task_id = task.get("task_id")
        if not parent_task_id:
            self.log.error("Missing task_id in agent_task")
            return

        current_desc = task.get("description") or task.get("content", "")
        self.task_id_to_sender[parent_task_id] = sender

        # === 阶段一：意图分类 ===
        intent = self._llm_classify_task_intent(current_desc, decision_context)

          # === 如果是针对历史任务的操作 ===
        if intent_type != "new_task":
            target_task = self._resolve_target_task(intent["target_task_reference"])
            if not target_task:
                self.send(sender, {"error": "未找到相关任务", "reference": intent["target_task_reference"]})
                return

            # 路由到对应处理器
            if intent_type == "comment_on_task":
                self._handle_add_comment(target_task, intent["comment_text"], sender)
            elif intent_type == "revise_result":
                self._handle_revise_result(target_task, intent["revision_content"], sender)
            elif intent_type == "re_run_task":
                self._handle_re_run_task(target_task, sender)
            elif intent_type == "cancel_task":
                self._handle_cancel_any_task(target_task, sender)
            elif intent_type in ["trigger_existing", "modify_loop_interval", "pause_loop", "resume_loop"]:
                # 转发给循环调度器（需确保是 loop 类型）
                if target_task.get("type") == "loop":
                    self._forward_to_loop_scheduler(intent, target_task["task_id"], sender)
                else:
                    self.send(sender, {"error": "该任务不是循环任务"})
            else:
                self.send(sender, {"error": "不支持的操作类型"})

    # === 否则：处理新任务 ===



            # === Step 1: 路由决策 ===
            decision_context = self.memory_cap.build_conversation_context(current_input=current_desc)
            decision = self._llm_decide_task_strategy(current_desc, decision_context)

            if decision.get("is_loop", True):
                self.add_loop_task(task, sender)
                
            

        needs_vault = decision.get("requires_sensitive_data", False)

        # === Step 2: 能力路由 ===
        if self.router:
            select_node_id = self.router.select_best_actor(
                agent_id=self.agent_id,
                user_input=task_desc,
                memory_context=context
            )
        if not select_node_id:
            self._dispatch_to_fallback(parent_task_id, decision_context, sender)
            return

        # === Step 3: 规划与分发子任务 ===
        try:
            plan = self._plan_subtasks(select_node_id, current_desc)
            pending_tasks = self._dispatch_subtasks(
                plan=plan,
                parent_task_id=parent_task_id,
                original_desc=current_desc,
                needs_vault=needs_vault
            )
        except Exception as e:
            self.log.error(f"Task planning/dispatch failed: {e}")
            self._report_error(parent_task_id, str(e), sender)
            return

        # === Step 4: 记录状态 & 写入记忆 ===
        self._aggregation_state[parent_task_id] = {
            "pending": pending_tasks,
            "results": {},
            "sender": sender
        }
        self.memory_cap.add_memory_intelligently(
            f"Started processing task: {current_desc} (ID: {parent_task_id})"
        )

    # ======================
    # 子任务结果处理（保持聚合逻辑不变）
    # ======================

    def add_loop_task(self, task: Dict[str, Any], sender: ActorAddress):
        """
        注意：Thespian Actor 是事件驱动的，不能阻塞。
        所以我们不在此启动 pika 消费者！
        而是让外部系统（或另一个 Actor）将 RabbitMQ 消息桥接到 Thespian。
        """
        self.log.info(f"Registering LOOP task: {parent_task_id}")
        
        # 构造循环执行的消息（当调度器触发时，会发回给自己）
        loop_execution_msg = {
            "message_type": "execute_loop_task",
            "original_task": task,
            "decision": decision
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

        # 回复用户：已注册循环任务
        self.send(sender, {
            "status": "loop_registered",
            "task_id": parent_task_id,
            "interval_sec": loop_interval,
            "reasoning": decision.get("reasoning", "")
        })
        return


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
            response = Generation.call(
                model="qwen-max",
                prompt=prompt,
                format="json",
                max_tokens=500,
                temperature=0.2
            )
            output = json.loads(response.output.text.strip())
            # 安全转换
            return {
                "intent_type": output.get("intent_type", "new_task"),
                "task_reference": output.get("task_reference", ""),
                "new_interval_sec": output.get("new_interval_sec"),
                "reasoning": output.get("reasoning", "")
            }
        except Exception as e:
            self.log.warning(f"Intent classification failed: {e}. Falling back to new_task.")
            return {"intent_type": "new_task", "task_reference": "", "new_interval_sec": None, "reasoning": str(e)}

    def _resolve_task_id_by_reference(self, reference: str) -> Optional[str]:
        """根据用户描述（如“日报”）匹配已注册的循环任务ID"""
        # 从记忆中查找最近的循环任务注册记录
        memories = self.manager.get_recent_memories(limit=20, keywords=["loop", "循环", "定时"])
        for mem in memories:
            content = mem.get("content", "").lower()
            if reference.lower() in content or reference.lower() in mem.get("task_id", ""):
                # 假设记忆中存了 task_id
                return mem.get("task_id")
        return None


    def _handle_trigger_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            self.send(sender, {"error": "未找到相关循环任务", "reference": ref})
            return

        # 向 LoopScheduler 发送“立即执行”消息（自定义类型）
        loop_scheduler = self.createActor(None, globalName="loop_scheduler")
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

        loop_scheduler = self.createActor(None, globalName="loop_scheduler")
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

        loop_scheduler = self.createActor(None, globalName="loop_scheduler")
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
        task_id = task["task_id"]
        self.manager.add_comment_to_task(task_id, comment)
        self.send(sender, {"status": "comment_added", "task_id": task_id})

    def _handle_revise_result(self, task: dict, new_content: str, sender: ActorAddress):
        # 简单策略：全量替换；高级策略：结构化 patch
        self.manager.update_task_result(task["task_id"], new_content)
        self.send(sender, {"status": "result_revised", "task_id": task["task_id"]})

    def _handle_re_run_task(self, task: dict, sender: ActorAddress):
        # 重新提交原任务描述
        new_task_msg = {
            "task_id": f"{task['task_id']}_retry_{int(time.time())}",
            "description": task["description"],
            "original_task_id": task["task_id"]  # 用于追踪
        }
        self._execute_one_time_task(new_task_msg, sender)
    
    def _handle_cancel_any_task(self, task: dict, sender: ActorAddress):
        if task["type"] == "loop":
            self._forward_to_loop_scheduler({"type": "cancel_loop_task", "task_id": task["task_id"]}, sender)
        else:
            # 普通任务：标记为 cancelled（若还在运行，可发取消信号）
            self.manager.mark_task_cancelled(task["task_id"])
            self.send(sender, {"status": "task_cancelled", "task_id": task["task_id"]})


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
        scheduler = self.createActor(None, globalName="loop_scheduler")
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
        task_id = result_msg.get("task_id")
        if not task_id or "." not in task_id:
            return
        parent_id = task_id.split(".")[0]
        state = self._aggregation_state.get(parent_id)
        if not state:
            return
        state["results"][task_id] = result_msg.get("result", {})
        state["pending"].discard(task_id)
        if not state["pending"]:
            self._finalize_aggregation(parent_id, state)

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
        self.send(sender, SubtaskResult(task_id=parent_task_id, result=final_result))
        if self.memory_cap:
            self.memory_cap.add_memory_intelligently(f"Task completed: {parent_task_id}")

    # ======================
    # 私有辅助方法（按职责拆分）
    # ======================

    def _ensure_memory_ready(self) -> bool:
        if self.memory_cap is None or not self.memory_cap.is_initialized:
            self.log.error("Memory capability not ready")
            return False
        return True

    def _plan_subtasks(self, node_id: str, goal: str) -> List[Dict[str, Any]]:
        planning_context = self.memory_cap.build_planning_context(planning_goal=goal)
        return self._task_coordinator.plan_subtasks(node_id, planning_context)

    def _dispatch_subtasks(
        self,
        plan: List[Dict[str, Any]],
        parent_task_id: str,
        original_desc: str,
        needs_vault: bool
    ) -> Set[str]:
        pending = set()
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

            from new.capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor
            child_addr = self.createActor(TaskGroupAggregatorActor, globalName=child_cap)

            self.send(child_addr, TaskMessage(task_id=child_task_id, context=final_child_context))
            pending.add(child_task_id)

            self._report_event("subtask_spawned", child_task_id, {
                "parent_task_id": parent_task_id,
                "capability": child_cap,
                "child_address": str(child_addr)
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
        fallback_addr = self.createActor(McpLlmActor)
        self.send(fallback_addr, McpFallbackRequest(task_id=task_id, context=context))
        self._aggregation_state[task_id] = {
            "pending": {"MCP_FALLBACK_TASK"},
            "results": {},
            "sender": sender
        }

    def _capability_to_actor_class(self, capability: str):
        actor_cls = ACTOR_REGISTRY.get(capability)
        if not actor_cls:
            raise ValueError(f"Unknown capability: {capability}")
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
            from new.capabilities.llm.qwen_adapter import QwenAdapter
            llm = QwenAdapter()
            result = llm.generate_text(prompt, max_tokens=300)

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