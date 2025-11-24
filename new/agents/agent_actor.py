from typing import Dict, Any, Optional, List
import logging
from datetime import datetime

# 从原始模块导入必要的类和函数
from new.capabilities.llm_memory.manager import UnifiedMemoryManager


from thespian.actors import Actor, ActorAddress
from typing import Dict, Any, Optional, Set
import logging
from datetime import datetime

# 假设这些模块存在（请替换为你的实际路径）
from new.capabilities.llm_memory.manager import UnifiedMemoryManager
from your_module.task_coordinator import TaskCoordinator
from your_module.messages import (
    TaskMessage,
    McpFallbackRequest,
    SubtaskResult,
    SubtaskError
)
from your_module.actors import McpLlmActor  # 继承 Actor 的 fallback actor

logger = logging.getLogger(__name__)

class AgentActor(Actor):  # ←←← 关键：继承 Thespian 的 Actor
    def __init__(self):
        super().__init__()
        self.agent_id: str = ""
        self.manager: Optional[UnifiedMemoryManager] = None
        self._task_coordinator = TaskCoordinator()
        self._aggregation_state: Dict[str, Dict] = {}
        self.task_id_to_sender: Dict[str, ActorAddress] = {}

    def receiveMessage(self, message: Any, sender: ActorAddress):
        try:
            if isinstance(message, dict) and "message_type" in message:
                msg_type = message["message_type"]
                if msg_type == "init":
                    self._handle_init(message, sender)
                elif msg_type == "agent_task":
                    self._handle_task(message, sender)
                elif msg_type == "subtask_result":
                    self._handle_execution_result(message, sender)
                elif msg_type == "subtask_error":
                    self._handle_execution_error(message, sender)
                else:
                    self.log.warning(f"Unknown message type: {msg_type}")
            elif isinstance(message, SubtaskResult):
                self._handle_execution_result(message.__dict__, sender)
            elif isinstance(message, SubtaskError):
                self._handle_execution_error(message.__dict__, sender)
            else:
                logger.warning(f"Unknown message type: {type(message)}")

        except Exception as e:
            logger.exception(f"Error in AgentActor {self.agent_id}: {e}")

    def _handle_init(self, msg: Dict[str, Any], sender: ActorAddress):
        self.agent_id = msg["agent_id"]
        self.manager = UnifiedMemoryManager(user_id=self.agent_id)
        self.log = logging.getLogger(f"AgentActor_{self.agent_id}")
        self.send(sender, {"status": "initialized", "agent_id": self.agent_id})

    def _handle_task(self, task: Dict[str, Any], sender: ActorAddress):
        parent_task_id = task.get("task_id")
        if not parent_task_id:
            self.log.error("Missing task_id in agent_task")
            return

        self.task_id_to_sender[parent_task_id] = sender

        # === Step 1: 构建复合上下文（六类记忆）===
        current_desc = task.get("description") or task.get("content", "")
        context_for_decision = self.manager.build_task_context_for_llm(
            current_task=current_desc,
            session_id=parent_task_id,
            include_vault=False
        )

        # === Step 2: LLM 判断任务性质 ===
        decision = self._llm_decide_task_strategy(current_desc, context_for_decision)
        is_loop = decision.get("is_loop", False)
        needs_vault = decision.get("requires_sensitive_data", False)

        if is_loop:
            self.log.info(f"Loop task detected: {parent_task_id} (not implemented)")
            self._execute_as_leaf(task, parent_task_id, sender)
            return

        # === Step 3: 路由到最佳子能力节点 ===
        select_node_id = self._task_coordinator._select_best_actor(self.agent_id, context_for_decision)
        pending: Set[str] = set()

        if not select_node_id:
            # === Fallback to MCP LLM Actor ===
            self.log.warning(f"No child found for {parent_task_id}, using fallback")
            fallback_addr = self.createActor(McpLlmActor)
            self.send(fallback_addr, McpFallbackRequest(
                task_id=parent_task_id,
                context=context_for_decision
            ))
            pending.add("MCP_FALLBACK_TASK")
        else:
            # === Step 4: 规划子任务（含 vault 上下文）===
            planning_context = self.manager.build_task_context_for_llm(
                current_task=current_desc,
                session_id=parent_task_id,
                include_vault=needs_vault
            )
            try:
                plan = self._task_coordinator.plan_subtasks(select_node_id, planning_context)
            except Exception as e:
                self.log.error(f"Planning failed: {e}")
                self._report_error(parent_task_id, str(e), sender)
                return

            # === Step 5: 分发子任务 ===
            for i, step in enumerate(plan):
                child_cap = step["node_id"]
                child_task_id = f"{parent_task_id}.child_{i}"

                # 获取或创建子 Actor（按 capability 注册名）
                try:
                    child_addr = self.createActor(
                        # 假设你有一个 registry 将 capability 映射到 Actor 类
                        self._capability_to_actor_class(child_cap),
                        globalName=child_cap  # 全局唯一名称，避免重复创建
                    )
                except Exception as e:
                    self.log.error(f"Failed to create child actor {child_cap}: {e}")
                    self._report_error(parent_task_id, f"Child actor creation failed: {e}", sender)
                    return

                # 为子任务构建专属上下文
                child_desc = step.get("description", "")
                child_memory_ctx = self.manager.build_task_context_for_llm(
                    current_task=child_desc,
                    session_id=parent_task_id,
                    include_vault=needs_vault
                )
                child_intent_params = step.get("intent_params", {})
                final_child_context = {
                    "memory_context": child_memory_ctx,
                    "instructions": child_intent_params,
                    "original_task": current_desc,
                    "capability": child_cap
                }

                # 发送子任务（Thespian 方式）
                self.send(child_addr, TaskMessage(
                    task_id=child_task_id,
                    context=final_child_context
                ))
                pending.add(child_task_id)

                self._report_event("subtask_spawned", child_task_id, {
                    "parent_task_id": parent_task_id,
                    "capability": child_cap,
                    "child_address": str(child_addr)
                })

        # === Step 6: 记录聚合状态 ===
        self._aggregation_state[parent_task_id] = {
            "pending": pending,
            "results": {},
            "sender": sender
        }

        # === Step 7: 记忆记录 ===
        self.manager.add_episodic_memory(
            content=f"Started processing task: {current_desc} (ID: {parent_task_id})",
            timestamp=datetime.now().isoformat()
        )

    def _capability_to_actor_class(self, capability: str):
        """
        根据 capability 名称返回对应的 Actor 类
        你需要实现这个映射（例如从注册表读取）
        """
        from your_module.actor_registry import ACTOR_REGISTRY
        actor_cls = ACTOR_REGISTRY.get(capability)
        if not actor_cls:
            raise ValueError(f"Unknown capability: {capability}")
        return actor_cls

    def _llm_decide_task_strategy(self, task_desc: str, context: str) -> Dict[str, Any]:
        decision_prompt = f"""
            你是一个智能任务调度器。请根据以下信息判断任务执行策略。

            [当前任务]
            {current_task_desc}

            [可用上下文]
            {context_for_decision}

            请严格按 JSON 格式回答：
            {{
            "is_loop": boolean,
            "is_parallel": boolean,
            "requires_sensitive_data": boolean,
            "reasoning": "简要说明"
            }}
            """
        try:
            decision = self._call_llm_json(decision_prompt)
            is_loop = decision.get("is_loop", False)
            is_parallel = decision.get("is_parallel", False)
            needs_vault = decision.get("requires_sensitive_data", False)
        except Exception as e:
            self.logger.warning(f"LLM 决策失败，使用默认策略: {e}")
            is_loop = False
            is_parallel = False
            needs_vault = False

    def _report_event(self, event_type: str, task_id: str, details: Dict[str, Any]):
        self.log.info(f"[{event_type}] {task_id}: {details}")

    def _report_error(self, task_id: str, error: str, sender: ActorAddress):
        self.send(sender, SubtaskError(task_id=task_id, error=error))

    def _execute_as_leaf(self, task: Dict[str, Any], task_id: str, sender: ActorAddress):
        # 简化叶子执行（可替换为真实执行）
        result = {"status": "executed_by_parent", "output": "Leaf execution stub"}
        self.send(sender, SubtaskResult(task_id=task_id, result=result))

    # ====== 子任务结果聚合 ======
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
            # 可选：立即失败或继续等待

    def _finalize_aggregation(self, parent_task_id: str, state: Dict[str, Any]):
        sender = state["sender"]
        final_result = {
            "status": "completed",
            "subtask_results": state["results"]
        }
        self.send(sender, SubtaskResult(task_id=parent_task_id, result=final_result))

        # 记忆记录
        self.manager.add_episodic_memory(
            content=f"Task completed: {parent_task_id}",
            timestamp=datetime.now().isoformat()
        )