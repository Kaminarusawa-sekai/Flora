# agent/agent_actor.py
import logging
from typing import Dict, Any, Optional, Callable
from datetime import timezone
from thespian.actors import Actor, WakeupMessage
import requests

from .memory.memory_actor import MemoryActor
from .memory.memory_interface import LoadMemoryForAgent, MemoryResponse
from .utils.data_scope import matches_data_scope
from .coordination.task_coordinator import TaskCoordinator
from .coordination.result_aggregator import ResultAggregator
from .coordination.swarm_coordinator import SwarmCoordinator
from .optimization.optimizer import Optimizer
from agent.io.data_query_actor import DataQueryActor, DataQueryRequest, DataQueryResponse
from agent.message import (
    InitMessage,
    TaskMessage,
    SubtaskResultMessage,
    SubtaskErrorMessage,
    OptimizationWakeup,
    MessageType
)

logger = logging.getLogger(__name__)


class AgentActor(Actor):
    def __init__(self):
        super().__init__()
        # 基础属性
        self.agent_id: str = ""
        self._is_leaf: bool = False
        self._self_info: Dict = {}
        self._capabilities: list = []
        self._dispatch_rules: Dict = {}
        self._memory_key: Optional[str] = None

        # 状态管理
        self._aggregation_state: Dict[str, Dict] = {}
        self._pending_memory_requests: Dict[str, Dict] = {}
        self._pending_data_requests: Dict[str, Dict] = {}
        self._actor_ref_cache: Dict[str, Any] = {}
        self._initialized: bool = False

        # 依赖注入（由 InitMessage 提供）
        self.registry = None
        self.orchestrator = None
        self.data_resolver = None
        self._neo4j_recorder = None

        self._fetch_data_fn: Optional[Callable] = None
        self._acquire_resources_fn: Optional[Callable] = None
        self._execute_capability_fn: Optional[Callable] = None
        self._execute_self_capability_fn: Optional[Callable] = None
        self._evaluator: Optional[Callable] = None
        self._improver: Optional[Callable] = None

        # 内部组件
        self._memory_actor = None
        self._data_query_actor = None
        self._task_coordinator = None
        self._swarm_coordinator = None
        self._optimizer = None
        self._optimization_interval: int = 3600

    def receiveMessage(self, msg, sender):
        try:
            if isinstance(msg, InitMessage):
                self._handle_init(msg)
            elif isinstance(msg, TaskMessage):
                self._handle_task(msg, sender)
            elif isinstance(msg, SubtaskResultMessage):
                self._handle_subtask_completion(msg.task_id, msg.result)
            elif isinstance(msg, SubtaskErrorMessage):
                self._handle_subtask_error(msg.task_id, msg.error)
            elif isinstance(msg, MemoryResponse):
                self._handle_memory_response(msg.key, msg.value, sender)
            elif isinstance(msg, DataQueryResponse):
                self._handle_data_response(msg)
            elif isinstance(msg, OptimizationWakeup):
                self._run_optimization_cycle()
                if not self._is_leaf and self._optimization_interval > 0:
                    self.wakeupAfter(self._optimization_interval, payload=OptimizationWakeup())
            else:
                logger.warning(f"Unknown message type: {type(msg)}")
        except Exception as e:
            logger.exception(f"Error in AgentActor {self.agent_id}: {e}")

    def _handle_init(self, msg: InitMessage):
        # 基础信息
        self.agent_id = msg.agent_id
        self._capabilities = msg.capabilities

        self._memory_key = msg.memory_key
        self._optimization_interval = msg.optimization_interval

        # 依赖注入
        self.registry = msg.registry
        self.orchestrator = msg.orchestrator
        self.data_resolver = msg.data_resolver
        self._neo4j_recorder = msg.neo4j_recorder

        self._fetch_data_fn = msg.fetch_data_fn
        self._acquire_resources_fn = msg.acquire_resources_fn
        self._evaluator = msg.evaluator
        self._improver = msg.improver

        # 获取自身注册信息（用于校验 capabilities 和 data_scope）
        if self.registry:
            self._self_info = self.registry.get_agent_meta(self.agent_id)
            if not self._self_info:
                raise ValueError(f"Agent {self.agent_id} not found in registry")
            self._is_leaf = self._self_info.get("is_leaf", self._is_leaf)

        # 创建内部 Actor
        if hasattr(self, 'createActor'):
            self._memory_actor = self.createActor(MemoryActor)
            self._data_query_actor = self.createActor(DataQueryActor)

            # 加载记忆
            if self._memory_key:
                self.send(self._memory_actor, LoadMemoryForAgent(self.agent_id))

        # 初始化协调器与优化器
        self._task_coordinator = TaskCoordinator(self.registry)
        self._swarm_coordinator = SwarmCoordinator(self.registry, self.data_resolver)
        self._optimizer = Optimizer(
            evaluator=self._evaluator,
            improver=self._improver,
            neo4j_recorder=self._neo4j_recorder,
            execute_fn=self._execute_self_capability_fn
        )

        self._initialized = True

        # 启动优化循环（仅非叶子节点）
        if not self._is_leaf and self._optimization_interval > 0:
            self.wakeupAfter(self._optimization_interval, payload=OptimizationWakeup())

        logger.info(f"AgentActor {self.agent_id} initialized (leaf={self._is_leaf})")

    def _handle_task(self, task_msg: TaskMessage, original_sender):
        
        print(f"[AgentActor {self.agent_id}] Received task {task_msg.task_id} with context keys: {list(task_msg.context.keys())}")
        
        self._report_event("started", task_msg.task_id, {
            "context_keys": list(task_msg.context.keys()),
            "is_leaf": self._is_leaf
        })

        # 能力与数据范围校验

        # if not matches_data_scope(self._self_info.get("data_scope", {}), task_msg.context):
        #     raise RuntimeError(f"Context violates data_scope for agent {self.agent_id}")

        ##TODO: 记忆补充待实现
        # if self._memory_actor and self._memory_key:
        #         self.send(self._memory_actor, LoadMemoryForAgent(self.agent_id))
        #         self._pending_memory_requests[task_msg.task_id] = {
        #             "context": task_msg.context,
        #             "sender": original_sender
        #         }
            # else:
            #     # 无记忆直接执行

        if self._is_leaf:
            # 叶子节点：先加载记忆，再决定是否需要查数据
            
            self._execute_leaf_task(task_msg.task_id, task_msg.context, {}, original_sender)
        else:
            self._execute_intermediate(task_msg.task_id,  task_msg.context, original_sender)

    def _handle_memory_response(self, key: str, memory_value: Any, sender):
        if not self._pending_memory_requests:
            return

        # 取出第一个（实际应按 key 或 task_id 匹配，此处简化）
        task_id, task_info = next(iter(self._pending_memory_requests.items()))
        del self._pending_memory_requests[task_id]

        memory = {"user_pref": memory_value} if memory_value else {}

        # 判断是否需要查数据（示例：仅特定 capability）
        if task_info["capability"] == "book_flight":
            self._fetch_data_for_task(
                task_id=task_id,
                query="SELECT * FROM flights WHERE user='alice'",  # 实际应由 capability 决定
                capability=task_info["capability"],
                context=task_info["context"],
                memory=memory,
                sender=task_info["sender"]
            )
        else:
            self._execute_leaf_task(
                task_id, task_info["capability"], task_info["context"], memory, task_info["sender"]
            )

    

    def _execute_leaf_task(self, task_id: str,  context: Dict, memory: Dict, sender, capability: str="dify_workflow"):
        try:
            if capability == "dify_workflow":
                # === Dify Workflow 执行逻辑 ===
                api_key = context.get("dify_api_key")
                base_url = context.get("dify_base_url", "https://api.dify.ai/v1")
                inputs = context.get("inputs", {})
                user = context.get("user", "thespian_user")

                if not api_key:
                    raise ValueError("Missing 'dify_api_key' in context")
                if not isinstance(inputs, dict):
                    raise ValueError("'inputs' must be a dictionary")

                # 调用 Dify Workflow API
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "inputs": inputs,
                    "response_mode": "blocking",
                    "user": user
                }

                url = f"{base_url.rstrip('/')}/workflows/run"
                resp = requests.post(url, json=payload, headers=headers, timeout=60)
                resp.raise_for_status()
                data = resp.json()

                # 提取输出结果
                outputs = data.get("data", {}).get("outputs", {})
                workflow_run_id = data.get("workflow_run_id")
                status = data.get("data", {}).get("status")

                result = {
                    "outputs": outputs,
                    "workflow_run_id": workflow_run_id,
                    "status": status,
                    "raw_response": data  # 可选：保留原始响应用于调试
                }

            else:
                # 其他 capability 交给原有逻辑处理
                result = self._execute_capability_fn(capability, context, memory)

            # 发送成功结果
            self.send(sender, SubtaskResultMessage(task_id, result))
            self._report_event("finished", task_id, {"result_preview": str(result)[:200]})

        except Exception as e:
            error_msg = str(e)
            self.send(sender, SubtaskErrorMessage(task_id, error_msg))
            self._report_event("failed", task_id, {"error": error_msg[:200]})


    def _fetch_data_for_task(self, task_id: str, query: str, capability: str, context: Dict, memory: Dict, sender):
         # 不再需要 memory！DataQueryActor 自己会加载
        request_id = f"data_req_{task_id}"
        self._pending_data_requests[request_id] = {
            "task_id": task_id,
            "sender": sender
        }
        self.send(self._data_query_actor, DataQueryRequest(request_id=request_id, query=query))

    def _handle_data_response(self, response: DataQueryResponse):
        req_id = response.request_id
        if req_id not in self._pending_data_requests:
            logger.warning(f"Orphaned data response for {req_id}")
            return

        info = self._pending_data_requests.pop(req_id)
        if response.error:
            self.send(info["sender"], SubtaskErrorMessage(info["task_id"], response.error))
            return

        enhanced_context = {**info["context"], "db_result": response.result}
        self._execute_leaf_task(
            info["task_id"], info["capability"], enhanced_context, info["memory"], info["sender"]
        )

    def _execute_intermediate(self, parent_task_id: str, context: Dict, original_sender):
        select_node_id=self._task_coordinator._select_best_actor(self.agent_id, context)
        if not select_node_id:
            raise RuntimeError(f"No suitable child agent found for task {parent_task_id}")
        
        plan = self._task_coordinator.plan_subtasks(select_node_id, context)
        print(plan)
        pending = set()
        for i, step in enumerate(plan):
            child_cap = step["node_id"]
            child_ctx = self._task_coordinator.resolve_context({**context, **step.get("intent_params", {})},self.agent_id)
            # child_info = self.registry.find_direct_child_by_capability(self.agent_id, child_cap, child_ctx)
            # if not child_info:
            #     raise RuntimeError(f"No child agent for capability {child_cap} under {self.agent_id}")

            child_ref = self._get_or_create_actor_ref(step["node_id"])
            child_task_id = f"{parent_task_id}.child_{i}"

            self._report_event("subtask_spawned", child_task_id, {
                "parent_task_id": parent_task_id,
                "capability": child_cap,
                "agent_id": step["node_id"]
            })

            self.send(child_ref, TaskMessage(child_task_id, child_ctx))
            pending.add(child_task_id)

        self._aggregation_state[parent_task_id] = {
            "pending": pending,
            "results": {},
            "sender": original_sender
        }

    def _handle_subtask_completion(self, task_id: str, result: Any):
        self._report_event("finished", task_id, {"result_preview": str(result)[:200]})
        self._complete_or_aggregate(task_id, result)

    def _handle_subtask_error(self, task_id: str, error: str):
        self._report_event("failed", task_id, {"error": str(error)[:200]})
        self._complete_or_aggregate(task_id, error, is_error=True)

    def _complete_or_aggregate(self, task_id: str, result_or_error: Any, is_error: bool = False):
        parent_id = self._get_parent_task_id(task_id)
        if parent_id not in self._aggregation_state:
            return  # 可能是顶层任务，无需聚合

        state = self._aggregation_state[parent_id]
        if is_error:
            # 简化：任一子任务失败即失败
            del self._aggregation_state[parent_id]
            self.send(state["sender"], SubtaskErrorMessage(parent_id, f"Subtask {task_id} failed: {result_or_error}"))
            return

        state["results"][task_id] = result_or_error
        state["pending"].discard(task_id)

        if not state["pending"]:
            final_result = ResultAggregator.aggregate_sequential(state["results"])
            self.send(state["sender"], SubtaskResultMessage(parent_id, final_result))
            del self._aggregation_state[parent_id]

    def _get_parent_task_id(self, task_id: str) -> str:
        return task_id.rsplit(".", 1)[0] if "." in task_id else ""

    def _get_or_create_actor_ref(self, agent_id: str):
        if agent_id not in self._actor_ref_cache:
            ref = self.createActor(AgentActor)
            # 构造 InitMessage（需从 registry 获取完整配置）
            agent_info = self.registry.get_agent_meta(agent_id)
            if not agent_info:
                raise ValueError(f"Cannot create actor for unknown agent: {agent_id}")

            init_msg = InitMessage(

                agent_id=agent_id,
                capabilities=agent_info["capability"],           # Leaf: ["book_flight"]; Branch: ["route_flight"]
                memory_key = agent_id,       # 默认 = agent_id
                registry=self.registry,
                # agent_id=agent_id,
                # is_leaf=agent_info.get("is_leaf", False),
                # capabilities=agent_info.get("capabilities", []),
                # dispatch_rules=agent_info.get("dispatch_rules", {}),
                # memory_key=agent_info.get("memory_key"),
                # registry=self.registry,
                # orchestrator=self.orchestrator,
                # data_resolver=self.data_resolver,
                # neo4j_recorder=self._neo4j_recorder,
                # fetch_data_fn=self._fetch_data_fn,
                # acquire_resources_fn=self._acquire_resources_fn,
                # execute_capability_fn=self._execute_capability_fn,
                # execute_self_capability_fn=self._execute_self_capability_fn,
                # evaluator=self._evaluator,
                # improver=self._improver,
                # optimization_interval=self._optimization_interval
            )
            self.send(ref, init_msg)
            self._actor_ref_cache[agent_id] = ref
        return self._actor_ref_cache[agent_id]

    def _run_optimization_cycle(self):
        try:
            # TODO: 实际应从历史任务或性能指标生成优化任务
            logger.debug(f"Running optimization cycle for {self.agent_id}")
            # self._optimizer.run_optimization_task(...)
        except Exception as e:
            logger.exception(f"Optimization cycle failed for {self.agent_id}: {e}")

    def _report_event(self, event_type: str, task_id: str, details: Dict):
        if self.orchestrator:
            self.orchestrator.report_event(event_type, task_id, details)