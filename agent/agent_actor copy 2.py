# agent_actor.py（重构版：纯组合 + 策略注入）

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Callable, Tuple
from datetime import datetime, timezone  # 用于修复 utcnow 警告
from copy import deepcopy
from thespian.actors import Actor, ActorTypeDispatcher, WakeupMessage


logger = logging.getLogger(__name__)

##TODO：要增加一个，数据如果不存在，则要返回错误，然后建立一个新任务来生成数据。

class OptimizationWakeup(WakeupMessage):
    """用于触发自优化循环的内部消息"""
    pass


class SwarmExecuteRequest:
    def __init__(self, capability: str, param_sets: List[Dict], base_context: Dict[str, Any]):
        self.capability = capability
        self.param_sets = param_sets
        self.base_context = base_context


class TaskMessage:
    def __init__(self, frame_id: str, capability: str, context: Dict[str, Any]):
        self.frame_id = frame_id
        self.capability = capability
        self.context = context


class SubtaskResultMessage:
    def __init__(self, parent_frame_id: str, sub_frame_id: str, result: Any):
        self.parent_frame_id = parent_frame_id
        self.sub_frame_id = sub_frame_id
        self.result = result


class SubtaskErrorMessage:
    def __init__(self, parent_frame_id: str, sub_frame_id: str, error: str):
        self.parent_frame_id = parent_frame_id
        self.sub_frame_id = sub_frame_id
        self.error = error



class SwarmTaskMessage:
    """Swarm 任务：由 Swarm 控制器发给某个 Leaf Actor"""
    def __init__(self, swarm_id: str, variant_id: str, capability: str, context: Dict[str, Any]):
        self.swarm_id = swarm_id      # 全局 Swarm ID
        self.variant_id = variant_id  # 当前变体 ID（如 "v0", "v1"）
        self.capability = capability
        self.context = context

class SwarmResultMessage:
    """Leaf Actor 返回 Swarm 结果"""
    def __init__(self, swarm_id: str, variant_id: str, result: Any):
        self.swarm_id = swarm_id
        self.variant_id = variant_id
        self.result = result

class SwarmErrorMessage:
    def __init__(self, swarm_id: str, variant_id: str, error: str):
        self.swarm_id = swarm_id
        self.variant_id = variant_id
        self.error = error

# 已有消息增强：支持层级追踪
class SubtaskResultMessage:
    def __init__(self, task_id: str, result: Any):  # 去掉 parent_frame_id，改用全局 task_id
        self.task_id = task_id
        self.result = result

class SubtaskErrorMessage:
    def __init__(self, task_id: str, error: str):
        self.task_id = task_id
        self.error = error



class AgentActorThespian(Actor, ActorTypeDispatcher):
    """
    Thespian-compatible AgentActor.
    All injected functions must be synchronous.
    """

    def __init__(self):
        super().__init__()
        self.agent_id: str = ""
        self._is_leaf: bool = False
        self._self_info: Dict = {}
        self._aggregation_state: Dict[str, Dict] = {}

        
        # Dependencies (to be injected via globalArgs or message)
        self.registry = None
        self.orchestrator = None
        self.data_resolver = None
        self.topo_sorter = None
        self._memory = None
        self._neo4j_recorder = None

        # Strategy functions (must be sync)
        self._fetch_data_fn: Callable = None
        self._acquire_resources_fn: Callable = None
        self._execute_capability_fn: Callable = None
        self._execute_self_capability_fn: Callable = None
        self._evaluator: Callable = None
        self._improver: Callable = None
        self._optuna_sampler: Optional[Callable] = None

        self._optimization_interval: int = 3600  # seconds

    # 在 Actor 内部
    def _get_or_create_actor_ref(self, agent_id: str):
        if agent_id not in self._actor_ref_cache:
            # 创建新 Actor（传递 init 消息）
            ref = self.createActor(AgentActorThespian)
            init_msg = self._build_init_message_for(agent_id)  # 从全局配置构建
            self.send(ref, init_msg)
            self._actor_ref_cache[agent_id] = ref
        return self._actor_ref_cache[agent_id]

    def receiveMessage(self, msg, sender):
        if isinstance(msg, SubtaskResultMessage):
            self._handle_subtask_completion(msg.task_id, msg.result)
        elif isinstance(msg, SubtaskErrorMessage):
            self._handle_subtask_error(msg.task_id, msg.error)
        elif isinstance(msg, SwarmResultMessage):
            self._handle_swarm_result(msg.swarm_id, msg.variant_id, msg.result)
        elif isinstance(msg, SwarmErrorMessage):
            self._handle_swarm_error(msg.swarm_id, msg.variant_id, msg.error)
        try:
            if isinstance(msg, dict) and msg.get("type") == "init":
                self._handle_init(msg)
            elif isinstance(msg, TaskMessage):
                self._handle_task(msg)
            elif isinstance(msg, SubtaskResultMessage):
                self.on_subtask_result(msg.parent_frame_id, msg.sub_frame_id, msg.result)
            elif isinstance(msg, SubtaskErrorMessage):
                self.on_subtask_error(msg.parent_frame_id, msg.sub_frame_id, msg.error)
            elif isinstance(msg, SwarmExecuteRequest):
                # 注意：Swarm 在 Thespian 中是同步阻塞执行（非并发）
                # 如需并发，需用子 Actor，但复杂度高；此处简化为顺序执行
                results = self._swarm_execute_sync(
                    msg.capability, msg.param_sets, msg.base_context
                )
                # 你可以选择将结果发回 sender，或记录
                self.send(sender, results)
            elif isinstance(msg, OptimizationWakeup):
                self._run_optimization_cycle()
                # 重新调度下一次
                self.wakeupAfter(self._optimization_interval, payload=OptimizationWakeup())
            else:
                logger.warning(f"Unknown message type: {type(msg)}")
        except Exception as e:
            logger.exception(f"Error in AgentActorThespian {self.agent_id}: {e}")
            if hasattr(msg, 'frame_id'):
                self.orchestrator.report_error(msg.frame_id, str(e))

    def _handle_init(self, init_msg: dict):
        """初始化 Actor（必须在第一条消息中完成）"""
        self.agent_id = init_msg["agent_id"]
        self.registry = init_msg["registry"]
        self.orchestrator = init_msg["orchestrator"]
        self.data_resolver = init_msg["data_resolver"]
        self.topo_sorter = init_msg["topo_sorter"]
        memory_loader = init_msg["memory_loader"]
        self._neo4j_recorder = init_msg["neo4j_recorder"]

        # Strategy functions
        self._fetch_data_fn = init_msg["fetch_data_fn"]
        self._acquire_resources_fn = init_msg["acquire_resources_fn"]
        self._execute_capability_fn = init_msg["execute_capability_fn"]
        self._execute_self_capability_fn = init_msg.get("execute_self_capability_fn")
        self._evaluator = init_msg["evaluator"]
        self._improver = init_msg["improver"]
        self._optuna_sampler = init_msg.get("optuna_sampler")
        self._optimization_interval = init_msg.get("optimization_interval", 3600)

        self._self_info = self.registry.get_agent_by_id(self.agent_id)
        if not self._self_info:
            raise ValueError(f"Agent {self.agent_id} not found in registry")

        self._is_leaf = self._self_info["is_leaf"]
        self._memory = memory_loader(self.agent_id)

        # 启动自优化循环（仅中间层）
        if not self._is_leaf:
            self.wakeupAfter(self._optimization_interval, payload=OptimizationWakeup())

    def _handle_task(self, task_msg: TaskMessage):
        frame_id = task_msg.frame_id
        capability = task_msg.capability
        context = task_msg.context

        if capability not in self._self_info["capabilities"]:
            raise RuntimeError(f"Agent {self.agent_id} does not support capability: {capability}")
        if not self._matches_data_scope(self._self_info["data_scope"], context):
            raise RuntimeError(f"Context does not satisfy data_scope of {self.agent_id}")

        if self._is_leaf:
            self._execute_leaf(frame_id, capability, context)
        else:
            self._execute_intermediate(frame_id, capability, context)

    def _execute_leaf(self, task_id: str, capability: str, context: Dict):
        # 上报：任务开始
        self.send(self._observer_ref, TaskEvent(
            "started", task_id, self.agent_id,
            {"capability": capability, "context_keys": list(context.keys())}
        ))

        try:
            result = self._execute_capability_fn(capability, context, self._memory)
            # 上报：任务完成
            self.send(self._observer_ref, TaskEvent("finished", task_id, self.agent_id))
            self.send(self._original_caller, SubtaskResultMessage(task_id, result))
        except Exception as e:
            self.send(self._observer_ref, TaskEvent("failed", task_id, self.agent_id, {"error": str(e)}))
            self.send(self._original_caller, SubtaskErrorMessage(task_id, str(e)))

    def _execute_intermediate(self, parent_task_id: str, capability: str, context: Dict):
        # 1. 决定要调用哪些子能力（可能多个）
        sub_capabilities = ["capA", "capB", "capC"]  # 可能来自拓扑排序或策略

        pending_tasks = set()
        for i, sub_cap in enumerate(sub_capabilities):
            # 2. 为每个子能力找一个合适的子 Actor
            child_info = self.registry.find_child_for_capability(self.agent_id, sub_cap, context)
            if not child_info:
                raise RuntimeError(f"No child for {sub_cap}")

            # 3. 生成唯一子任务 ID
            child_task_id = f"{parent_task_id}.child_{i}"

            # 4. 获取或创建子 Actor 引用（带缓存）
            child_actor_ref = self._get_or_create_child_actor(child_info["agent_id"])

            # 5. 发送任务（并发！）
            self.send(child_actor_ref, TaskMessage(
                frame_id=child_task_id,
                capability=sub_cap,
                context=context
            ))

            pending_tasks.add(child_task_id)

        # 6. 记录聚合状态：等待这些子任务完成
        self._aggregation_state[parent_task_id] = {
            "type": "parallel_branch",
            "pending": pending_tasks,
            "results": {},
            "original_sender": self._original_caller_ref  # 最终结果发回这里
        }

    def _extract_relevant_subgraph(self, start_cap: str, dependencies: List[Dict]) -> Set[str]:
        from collections import defaultdict, deque
        graph = defaultdict(list)
        all_nodes = set()
        for dep in dependencies:
            graph[dep["from"]].append(dep["to"])
            all_nodes.add(dep["from"])
            all_nodes.add(dep["to"])
        if start_cap not in all_nodes:
            return {start_cap}
        visited = set()
        queue = deque([start_cap])
        visited.add(start_cap)
        while queue:
            node = queue.popleft()
            for neighbor in graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        return visited


    def _handle_subtask_completion(self, task_id: str, result: Any):
        # 找到父任务（通过 task_id 的前缀）
        parent_id = self._get_parent_task_id(task_id)
        if parent_id in self._aggregation_state:
            state = self._aggregation_state[parent_id]
            state["results"][task_id] = result
            state["pending"].discard(task_id)
            if not state["pending"]:
                final_result = self._aggregate_results(state["results"])
                # 向上回调
                self.send(state["sender"], SubtaskResultMessage(parent_id, final_result))
                del self._aggregation_state[parent_id]

    def _get_parent_task_id(self, task_id: str) -> str:
        # "root.child_0.grand_0" -> "root.child_0"
        parts = task_id.rsplit(".", 1)
        return parts[0] if len(parts) > 1 else ""
    def _coordinate_subtasks(
        self,
        parent_task_id: str,
        execution_plan: List[Dict],
        original_context: Dict[str, Any]
    ):
        pending = set()
        child_actors = []

        for idx, step in enumerate(execution_plan):
            cap = step["node_id"]
            intent_params = step.get("intent_params", {})
            ctx = {**original_context, **intent_params}
            resolved_ctx = self.data_resolver.resolve(ctx)

            child_info = self.registry.find_direct_child_by_capability(self.agent_id, cap, ctx)
            if not child_info:
                raise RuntimeError(f"No child for {cap}")

            child_actor = self._get_or_create_actor_ref(child_info["agent_id"])
            child_task_id = f"{parent_task_id}.child_{idx}"

            # 发送任务给子 Actor
            task_msg = TaskMessage(
                frame_id=child_task_id,
                capability=cap,
                context=resolved_ctx
            )
            self.send(child_actor, task_msg)
            # 在 _coordinate_subtasks 中
            self.send(self._observer_ref, TaskEvent(
                "subtask_spawned",
                child_task_id,
                child_info["agent_id"],
                {"parent_task_id": parent_task_id, "capability": sub_cap}
            ))

            pending.add(child_task_id)
            child_actors.append(child_actor)

        # 记录聚合状态
        self._aggregation_state[parent_task_id] = {
            "type": "subtree",
            "pending": pending,
            "results": {},
            "sender": self.myAddress
        }

    def on_subtask_result(self, parent_frame_id: str, sub_frame_id: str, result: Any):
        state = self._aggregation_state.get(parent_frame_id)
        if not state:
            return
        state["results"][sub_frame_id] = result
        state["pending"].discard(sub_frame_id)
        if not state["pending"]:
            final_result = self._aggregate_results(state["results"])
            self.orchestrator.report_result(parent_frame_id, final_result)
            del self._aggregation_state[parent_frame_id]

    def on_subtask_error(self, parent_frame_id: str, sub_frame_id: str, error: str):
        if parent_frame_id in self._aggregation_state:
            del self._aggregation_state[parent_frame_id]
        self.orchestrator.report_error(parent_frame_id, error)

    def _aggregate_results(self, results: Dict[str, Any]) -> Any:
        return list(results.values())[-1] if results else None

    @staticmethod
    def _matches_data_scope(data_scope: Dict[str, Any], context: Dict[str, Any]) -> bool:
        return all(context.get(k) == v for k, v in data_scope.items())

    # ==============================
    # 自优化循环（同步版）
    # ==============================
    def _run_optimization_cycle(self):
        """执行一轮优化任务"""
        try:
            tasks = self._get_optimization_tasks()
            for task in tasks:
                self._run_optimization_task(task)
        except Exception as e:
            logger.exception(f"Optimization cycle error in {self.agent_id}: {e}")

    def _get_optimization_tasks(self) -> List[Dict]:
        return []  # 默认无任务，可扩展

    def _run_optimization_task(self, task: Dict):
        task_id = task["task_id"]
        capability = task["capability"]
        test_context = task.get("test_context", {})

        try:
            if self._is_leaf:
                memory_snapshot = deepcopy(self._memory) if self._memory is not None else None
                result = self._execute_capability_fn(capability, test_context, memory_snapshot)
            else:
                if self._execute_self_capability_fn is None:
                    raise NotImplementedError("execute_self_capability_fn not provided")
                result = self._execute_self_capability_fn(capability, test_context)

            score = self._evaluator(task_id, result)
            self._improver(task_id, score)

            self._neo4j_recorder.record_optimization_trial(
                agent_id=self.agent_id,
                task_id=task_id,
                params=test_context,
                result=result,
                score=score,
                timestamp=datetime.now(timezone.utc),
                mode="single"
            )
        except Exception as e:
            logger.error(f"Optimization task {task_id} failed: {e}")

    # ==============================
    # Swarm 执行（同步顺序版）
    # ==============================
    def _swarm_execute_concurrent(
        self,
        capability: str,
        param_sets: List[Dict],
        base_context: Dict[str, Any]
    ):
        swarm_id = f"swarm_{self.agent_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        pending = set()
        results = {}

        # 查找所有可用的同类 Leaf Actor（假设你有 registry.get_all_leaves_by_capability）
        leaf_agents = self.registry.get_all_leaves_by_capability(capability)
        if not leaf_agents:
            raise RuntimeError(f"No leaf agents found for capability {capability}")

        for i, params in enumerate(param_sets):
            variant_id = f"v{i}"
            ctx = {**base_context, **params}
            resolved_ctx = self.data_resolver.resolve(ctx)

            # 轮询或随机选择一个 Leaf（可扩展为负载均衡）
            target_agent = leaf_agents[i % len(leaf_agents)]
            target_actor = self._get_or_create_actor_ref(target_agent["agent_id"])

            msg = SwarmTaskMessage(swarm_id, variant_id, capability, resolved_ctx)
            self.send(target_actor, msg)

            pending.add(variant_id)

        # 记录状态
        self._aggregation_state[swarm_id] = {
            "type": "swarm",
            "pending": pending,
            "results": {},
            "sender": self.myAddress,  # 用于回调自己
            "capability": capability
        }

    # ==============================
    # 公共同步接口（策略函数已注入，直接调用）
    # ==============================
    def fetch_data(self, query: str) -> Any:
        return self._fetch_data_fn(query)

    def acquire_resources(self, purpose: str) -> int:
        return self._acquire_resources_fn(purpose)