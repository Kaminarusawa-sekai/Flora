# agent_actor.py（重构版：纯组合 + 策略注入）

import asyncio
import logging
from typing import Dict, List, Any, Optional, Set, Callable, Tuple
from datetime import datetime, timezone  # 用于修复 utcnow 警告
from copy import deepcopy

logger = logging.getLogger(__name__)

##TODO：要增加一个，数据如果不存在，则要返回错误，然后建立一个新任务来生成数据。

class AgentActor:
    """
    Concrete AgentActor with all behaviors injected at construction time.
    No inheritance needed — fully configurable via callables.
    """

    def __init__(
        self,
        agent_id: str,
        registry,
        orchestrator,
        data_resolver,
        topo_sorter,
        memory_loader: Callable[[str], Any],
        neo4j_recorder,
        # === 行为策略（替代抽象方法）===
        fetch_data_fn: Callable[[str], Any],
        acquire_resources_fn: Callable[[str], int],
        execute_capability_fn: Callable[[str, Dict, Any], Any],
        # === 优化器相关 ===
        evaluator: Callable[[str, Any], float],
        improver: Callable[[str, float], None],
        optimization_interval: int = 3600,
        # === 蜂群执行支持 ===
        optuna_sampler: Optional[Callable[[str], List[Dict]]] = None,
        # === 中间层自执行（可选）===
        execute_self_capability_fn: Optional[Callable[[str, Dict], Any]] = None,
        **kwargs
    ):
        self.capabilities = None,
        self.data_scope = None,
        self.is_leaf = None,
        self.orchestrator_callback = None,
        self.agent_id = agent_id
        self.registry = registry
        self.orchestrator = orchestrator
        self.data_resolver = data_resolver
        self.topo_sorter = topo_sorter
        self._memory = memory_loader(agent_id)
        self._neo4j_recorder = neo4j_recorder

        self._self_info = self.registry.get_agent_by_id(agent_id)
        if not self._self_info:
            raise ValueError(f"Agent {self.agent_id} not found")

        self._is_leaf = self._self_info["is_leaf"]
        self._aggregation_state = {}

        # === 注入的行为策略 ===
        self._fetch_data_fn = fetch_data_fn
        self._acquire_resources_fn = acquire_resources_fn
        self._execute_capability_fn = execute_capability_fn
        self._execute_self_capability_fn = execute_self_capability_fn

        # === 优化器组件（仅中间层启用）===
        self._evaluator = evaluator
        self._improver = improver
        self._optimization_interval = optimization_interval
        self._optimization_task: Optional[asyncio.Task] = None

        # === 蜂群支持 ===
        self._optuna_sampler = optuna_sampler

    # 注意：不再在这里 create_task！


    async def start(self):
        """启动后台优化任务（必须在 asyncio 事件循环中调用）"""
        if not self._is_leaf and self._optimization_task is None:
            self._optimization_task = asyncio.create_task(
                self._optimization_loop(self._optimization_interval)
            )

    async def stop(self):
        """停止优化任务"""
        if self._optimization_task is not None:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
            self._optimization_task = None
    # ==============================
    # 【1】自优化循环
    # ==============================
    async def _optimization_loop(self, interval: int):
        while True:
            try:
                tasks = await self._get_optimization_tasks()
                for task in tasks:
                    await self._run_optimization_task(task)
                await asyncio.sleep(interval)
            except Exception as e:
                logger.exception(f"Optimization loop error in {self.agent_id}: {e}")

    async def _get_optimization_tasks(self) -> List[Dict]:
        # 默认无任务，可由外部通过 monkey-patch 或子类化扩展（但不推荐）
        return []

    async def _run_optimization_task(self, task: Dict):
        task_id = task["task_id"]
        capability = task["capability"]
        test_context = task.get("test_context", {})

        try:
            if self._is_leaf:
                # 使用注入的函数，传入 memory 快照
                memory_snapshot = deepcopy(self._memory) if self._memory is not None else None
                result = self._execute_capability_fn(capability, test_context, memory_snapshot)
            else:
                if self._execute_self_capability_fn is None:
                    raise NotImplementedError("execute_self_capability_fn not provided for intermediate agent")
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
    # 【2】蜂群执行（并发）
    # ==============================
    async def swarm_execute(
        self,
        capability: str,
        param_sets: List[Dict],
        base_context: Dict[str, Any]
    ) -> List[Dict]:
        if self._optuna_sampler is None:
            raise RuntimeError("Optuna sampler not provided for swarm execution")

        async def _run_one(params: Dict) -> Dict:
            ctx = {**base_context, **params}
            if self._is_leaf:
                memory_snapshot = deepcopy(self._memory) if self._memory is not None else None
                result = self._execute_capability_fn(capability, ctx, memory_snapshot)
            else:
                if self._execute_self_capability_fn is None:
                    raise RuntimeError("Intermediate agent requires execute_self_capability_fn for swarm")
                result = self._execute_self_capability_fn(capability, ctx)

            self._neo4j_recorder.record_optimization_trial(
                agent_id=self.agent_id,
                task_id=f"swarm_{capability}",
                params=params,
                result=result,
                score=None,
                timestamp=datetime.now(timezone.utc),
                mode="swarm"
            )
            return {"params": params, "result": result}

        tasks = [_run_one(p) for p in param_sets]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        final_results = []
        for i, res in enumerate(results):
            if isinstance(res, Exception):
                logger.error(f"Swarm variant {i} failed: {res}")
                final_results.append({"params": param_sets[i], "result": None, "error": str(res)})
            else:
                final_results.append(res)
        return final_results

    # ==============================
    # 公共接口：替代原抽象方法
    # ==============================
    async def fetch_data(self, query: str) -> Any:
        """Public wrapper — handles sync/async automatically"""
        fn = self._fetch_data_fn
        result = fn(query)
        if asyncio.iscoroutine(result):
            result = await result
        return result

    async def acquire_resources(self, purpose: str) -> int:
        fn = self._acquire_resources_fn
        result = fn(purpose)
        if asyncio.iscoroutine(result):
            result = await result
        return result

    # ==============================
    # 主任务入口
    # ==============================
    def handle_task(self, frame_id: str, capability: str, context: Dict[str, Any]):
        try:
            if capability not in self._self_info["capabilities"]:
                raise RuntimeError(f"Agent {self.agent_id} does not support capability: {capability}")
            if not self._matches_data_scope(self._self_info["data_scope"], context):
                raise RuntimeError(f"Context does not satisfy data_scope of {self.agent_id}")

            if self._is_leaf:
                self._execute_leaf(frame_id, capability, context)
            else:
                self._execute_intermediate(frame_id, capability, context)
        except Exception as e:
            logger.exception(f"Error in handle_task for {self.agent_id}")
            self.orchestrator.report_error(frame_id, str(e))
            raise
        

    def _execute_leaf(self, frame_id: str, capability: str, context: Dict[str, Any]):
        try:
            memory_snapshot = deepcopy(self._memory) if self._memory is not None else None
            result = self._execute_capability_fn(capability, context, memory_snapshot)
            self.orchestrator.report_result(frame_id, result)
            self._neo4j_recorder.record_execution(
                agent_id=self.agent_id,
                capability=capability,
                context=context,
                result=result,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as e:
            self.orchestrator.report_error(frame_id, str(e))
 
    def _execute_intermediate(self, parent_frame_id: str, main_capability: str, original_context: Dict[str, Any]):
        try:
            my_capabilities = set(self._self_info["capabilities"])
            deps = self.registry.get_capability_dependencies(list(my_capabilities))
            relevant_capabilities = self._extract_relevant_subgraph(main_capability, deps)
            sorted_caps = self.topo_sorter.sort(relevant_capabilities, deps)
            execution_plan = [{"node_id": cap, "intent_params": {}} for cap in sorted_caps]
            self._coordinate_subtasks(parent_frame_id, execution_plan, original_context)
        except Exception as e:
            logger.exception(f"Error in _execute_intermediate for {self.agent_id}")
            self.orchestrator.report_error(parent_frame_id, str(e))

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

    def _coordinate_subtasks(
        self,
        parent_frame_id: str,
        execution_plan: List[Dict],
        original_context: Dict[str, Any]
    ):
        pending_frames: Set[str] = set()
        for idx, step in enumerate(execution_plan):
            cap = step["node_id"]
            intent_params = step.get("intent_params", {})
            task_context = {**original_context, **intent_params}
            child = self.registry.find_direct_child_by_capability(
                parent_agent_id=self.agent_id,
                capability=cap,
                context=task_context
            )
            if not child:
                raise RuntimeError(
                    f"No direct child under {self.agent_id} supports '{cap}' with context {task_context}"
                )
            resolved_context = self.data_resolver.resolve(task_context)
            sub_frame_id = f"{parent_frame_id}_{cap}_{idx}"
            pending_frames.add(sub_frame_id)
            self.orchestrator.submit_subtask(
                caller_agent_id=self.agent_id,
                target_agent_id=child["agent_id"],
                capability=cap,
                context=resolved_context,
                parent_frame_id=parent_frame_id
            )
        self._aggregation_state[parent_frame_id] = {
            "pending": pending_frames,
            "results": {},
            "expected_count": len(pending_frames)
        }

    # ========== 聚合回调 ==========
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


# aa=Actor()

# a = Actor()



# b = DataMaActor()
# a.ask("GetMessage", b)
# b.tell("Notify", a, **args)


# c=Actor()

# a.ask("Notify", c)
# c.ask("GetMessage", b)

# def DataMaActor():

#     def on_GetMessage(self, sender):
#         message = self.get_message_from_db()
#         sender.tell("HereIsMessage", self, message=message)
