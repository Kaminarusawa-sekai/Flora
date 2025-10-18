# agent/agent_actor.py
import logging
from typing import Dict, Any, Optional,Callable
from datetime import datetime, timezone
from thespian.actors import Actor, ActorTypeDispatcher, WakeupMessage

from .memory.memory_actor import MemoryActor
from .memory.memory_interface import LoadMemoryForAgent, MemoryResponse
from .utils.data_scope import matches_data_scope
from .coordination.task_coordinator import TaskCoordinator
from .coordination.result_aggregator import ResultAggregator
from .coordination.swarm_coordinator import SwarmCoordinator
from .optimization.optimizer import Optimizer
from agent.io.data_query_actor import DataQueryActor, DataQueryRequest, DataQueryResponse
from agent.message import InitMessage, TaskMessage, SubtaskResultMessage, SubtaskErrorMessage, OptimizationWakeup,MessageType


#

import logging
from typing import Dict, Any, Optional, Callable
from thespian.actors import Actor  # 只导入Actor，不需要ActorTypeDispatcher
from enum import Enum

logger = logging.getLogger(__name__)

# 定义消息类型枚举


# 定义消息类
# class InitMessage:
#     def __init__(self, agent_id: str, is_leaf: bool, capabilities: list, dispatch_rules: dict, 
#                  memory_key: Optional[str], registry=None, execute_capability_fn=None, 
#                  orchestrator=None, data_resolver=None, neo4j_recorder=None,
#                  fetch_data_fn=None, acquire_resources_fn=None, 
#                  execute_self_capability_fn=None, evaluator=None, 
#                  improver=None, optimization_interval: int = 3600):
#         self.agent_id = agent_id
#         self.is_leaf = is_leaf
#         self.capabilities = capabilities
#         self.dispatch_rules = dispatch_rules
#         self.memory_key = memory_key
#         self.registry = registry
#         self.execute_capability_fn = execute_capability_fn
#         self.orchestrator = orchestrator
#         self.data_resolver = data_resolver
#         self.neo4j_recorder = neo4j_recorder
#         self.fetch_data_fn = fetch_data_fn
#         self.acquire_resources_fn = acquire_resources_fn
#         self.execute_self_capability_fn = execute_self_capability_fn
#         self.evaluator = evaluator
#         self.improver = improver
#         self.optimization_interval = optimization_interval

# class LoadMemoryForAgent:
#     def __init__(self, agent_id: str):
#         self.agent_id = agent_id

class MemoryReadRequest:
    def __init__(self, key: str):
        self.key = key

class ResultAggregator:
    @staticmethod
    def aggregate_sequential(results: Dict[str, Any]) -> Any:
        # 简单聚合实现
        if len(results) == 1:
            return list(results.values())[0]
        return results

def matches_data_scope(data_scope: Dict, context: Dict) -> bool:
    # 简单的数据范围匹配实现
    return True

class AgentActor(Actor):
    """使用标准Actor实现的AgentActor"""
    
    def __init__(self):
        # 调用父类的初始化方法
        super().__init__()
        
        # 初始化实例变量
        self.agent_id: str = ""
        self._is_leaf: bool = False
        self._self_info: Dict = {}
        self._aggregation_state: Dict[str, Dict] = {}
        self._pending_memory_requests: Dict[str, Dict] = {}  # task_id -> {capability, context, sender}
        self._actor_ref_cache: Dict[str, Any] = {}
        self._observer_ref = None
        self.memory_key: Optional[str] = None
        
        # 注入的依赖
        self.registry = None
        self.orchestrator = None
        self.data_resolver = None
        self._neo4j_recorder = None
        
        # 策略函数（同步）
        self._fetch_data_fn: Callable = None
        self._acquire_resources_fn: Callable = None
        self._execute_capability_fn: Callable = None
        self._execute_self_capability_fn: Callable = None
        self._evaluator: Callable = None
        self._improver: Callable = None
        self._optuna_sampler: Optional[Callable] = None
        
        # 内部组件
        self._memory_actor = None
        self._task_coordinator = None
        self._swarm_coordinator = None
        self._optimizer = None
        self._optimization_interval = 3600
        
        # 在 AgentActor.__init__ 中新增
        self._data_query_actor = None
        self._pending_data_requests = {}  # request_id -> {task_id, capability, context, memory, sender}
        self._initialized = False
        self._pending_branch_tasks = {}
        self._dispatch_rules = {}

    def receiveMessage(self, msg, sender):
        """标准Actor的消息接收方法"""
        try:
            if isinstance(msg, dict) and msg.get("type") == MessageType.INIT.value:
                self._handle_init(msg)
            elif isinstance(msg, InitMessage):
                self._handle_init_from_obj(msg)
            elif isinstance(msg, TaskMessage):
                self._handle_task(msg, sender)
            elif isinstance(msg, SubtaskResultMessage):
                self._handle_subtask_completion(msg.task_id, msg.result)
            elif isinstance(msg, SubtaskErrorMessage):
                self._handle_subtask_error(msg.task_id, msg.error)
            elif isinstance(msg, MemoryResponse):
                self._handle_memory_response(msg.key, msg.value, sender)
            elif isinstance(msg, OptimizationWakeup):
                self._run_optimization_cycle()
                self.wakeupAfter(self._optimization_interval, payload=OptimizationWakeup())
            elif isinstance(msg, DataQueryResponse):
                self._handle_data_response(msg)
            elif isinstance(msg, WakeupMessage):
                self._process_optimization_queue()
            else:
                logger.warning(f"Unknown message: {type(msg)}")
        except Exception as e:
            logger.exception(f"Error in {self.agent_id}: {e}")

    def _handle_init(self, init_msg: dict):
        """处理字典格式的初始化消息"""
        # --- 基础初始化 ---
        self.agent_id = init_msg["agent_id"]
        self._is_leaf = init_msg.get("is_leaf", False)
        self._capabilities = init_msg.get("capabilities", [])
        self._dispatch_rules = init_msg.get("dispatch_rules", {})
        self._memory_key = init_msg.get("memory_key")

        # 依赖注入
        self.orchestrator = init_msg["orchestrator"]
        self.data_resolver = init_msg["data_resolver"]
        self._neo4j_recorder = init_msg["neo4j_recorder"]

        self._fetch_data_fn = init_msg["fetch_data_fn"]
        self._acquire_resources_fn = init_msg["acquire_resources_fn"]
        self._execute_capability_fn = init_msg["execute_capability_fn"]
        self._execute_self_capability_fn = init_msg.get("execute_self_capability_fn")
        self._evaluator = init_msg["evaluator"]
        self._improver = init_msg["improver"]
        self._optimization_interval = init_msg.get("optimization_interval", 3600)

        if self.registry:
            self._self_info = self.registry.get_agent_by_id(self.agent_id)
            if not self._self_info:
                raise ValueError(f"Agent {self.agent_id} not found")
            self._is_leaf = self._self_info["is_leaf"]

        # --- 创建内部组件 ---
        if hasattr(self, 'createActor'):
            self._memory_actor = self.createActor(MemoryActor)
            self.send(self._memory_actor, LoadMemoryForAgent(self.agent_id))

        self._task_coordinator = TaskCoordinator(self.registry, self.data_resolver)
        self._swarm_coordinator = SwarmCoordinator(self.registry, self.data_resolver)
        self._optimizer = Optimizer(
            evaluator=self._evaluator,
            improver=self._improver,
            neo4j_recorder=self._neo4j_recorder,
            execute_fn=self._execute_self_capability_fn
        )

        # 启动优化定时器（可选）
        if self._optimization_interval > 0:
            self._optimization_timer = self.wake_up_in(self._optimization_interval)

        self._initialized = True

        if not self._is_leaf:
            self.wakeupAfter(self._optimization_interval, payload=OptimizationWakeup())

    def _handle_init_from_obj(self, msg: InitMessage):
        """处理对象格式的初始化消息"""
        # --- 基础初始化 ---
        self.agent_id = msg.agent_id
        self._is_leaf = msg.is_leaf
        self._capabilities = None
        self._dispatch_rules = msg.dispatch_rules
        self._memory_key = msg.memory_key

        # 依赖注入
        self._registry = msg.registry
        self._execute_capability_fn = msg.execute_capability_fn
        self.orchestrator = msg.orchestrator
        self.data_resolver = msg.data_resolver
        self._neo4j_recorder = msg.neo4j_recorder

        self._fetch_data_fn = msg.fetch_data_fn
        self._acquire_resources_fn = msg.acquire_resources_fn
        self._execute_capability_fn = msg.execute_capability_fn
        self._execute_self_capability_fn = None
        self._evaluator = msg.evaluator
        self._improver = msg.improver
        self._optimization_interval = msg.optimization_interval

        if self.registry:
            self._self_info = self.registry.get_agent_by_id(self.agent_id)
            if not self._self_info:
                raise ValueError(f"Agent {self.agent_id} not found")
            self._is_leaf = self._self_info["is_leaf"]

        # --- 创建内部组件 ---
        if hasattr(self, 'createActor'):
            self._memory_actor = self.createActor(MemoryActor)
            self.send(self._memory_actor, LoadMemoryForAgent(self.agent_id))

        self._task_coordinator = TaskCoordinator(self.registry, self.data_resolver)
        self._swarm_coordinator = SwarmCoordinator(self.registry, self.data_resolver)
        self._optimizer = Optimizer(
            evaluator=self._evaluator,
            improver=self._improver,
            neo4j_recorder=self._neo4j_recorder,
            execute_fn=self._execute_self_capability_fn
        )

        # 启动优化定时器（可选）
        if self._optimization_interval > 0:
            self._optimization_timer = self.wake_up_in(self._optimization_interval)

        self._initialized = True

        if not self._is_leaf:
            self.wakeupAfter(self._optimization_interval, payload=OptimizationWakeup())

    def _handle_task(self, task_msg: TaskMessage, original_sender):
        self._report_event("started", task_msg.task_id, {
            "capability": task_msg.capability,
            "context_keys": list(task_msg.context.keys()),
            "is_leaf": self._is_leaf
        })
        
        if task_msg.capability not in self._self_info["capabilities"]:
            raise RuntimeError(f"Unsupported capability: {task_msg.capability}")
        if not matches_data_scope(self._self_info["data_scope"], task_msg.context):
            raise RuntimeError(f"Context violates data_scope")

        if self._is_leaf:
            # Leaf: 需要记忆 → 先查 MemoryActor
            if self._memory_actor:
                self.send(self._memory_actor, MemoryReadRequest(self._memory_key))
                self._pending_memory_requests[task_msg.task_id] = {
                    "capability": task_msg.capability,
                    "context": task_msg.context,
                    "sender": original_sender
                }
        else:
            # Intermediate: 直接协调子任务
            self._execute_intermediate(task_msg.task_id, task_msg.capability, task_msg.context, original_sender)

    def _handle_memory_response(self, key: str, memory_value, memory_actor_ref):
        if not self._pending_memory_requests:
            return

        task_id, task_info = next(iter(self._pending_memory_requests.items()))
        del self._pending_memory_requests[task_id]

        memory = {"user_pref": memory_value} if memory_value else {}

        # 假设 leaf 需要执行一个 DB 查询（示例）
        # 实际中，capability 决定是否需要查询
        if task_info["capability"] == "book_flight":
            self._fetch_data_for_task(
                task_id=task_id,
                query="SELECT * FROM flights WHERE user='alice'",
                capability=task_info["capability"],
                context=task_info["context"],
                memory=memory,
                sender=task_info["sender"]
            )
        else:
            # 无需 DB，直接执行
            try:
                result = self._execute_capability_fn(
                    task_info["capability"], task_info["context"], memory
                )
                self.send(task_info["sender"], SubtaskResultMessage(task_id, result))
            except Exception as e:
                self.send(task_info["sender"], SubtaskErrorMessage(task_id, str(e)))

    def _execute_intermediate(self, parent_task_id: str, capability: str, context: Dict, original_sender):
        plan = self._task_coordinator.plan_subtasks(self.agent_id, capability, context)
        pending = set()
        for i, step in enumerate(plan):
            child_cap = step["node_id"]
            child_ctx = self._task_coordinator.resolve_context({**context, **step.get("intent_params", {})})
            child_info = self.registry.find_direct_child_by_capability(self.agent_id, child_cap, child_ctx)
            if not child_info:
                raise RuntimeError(f"No child for {child_cap}")

            child_ref = self._get_or_create_actor_ref(child_info["agent_id"])
            child_task_id = f"{parent_task_id}.child_{i}"
            
            # 上报子任务派发
            self._report_event("subtask_spawned", child_task_id, {
                "parent_task_id": parent_task_id,
                "capability": child_cap,
                "agent_id": child_info["agent_id"]
            })
            
            self.send(child_ref, TaskMessage(child_task_id, child_cap, child_ctx))
            pending.add(child_task_id)

        self._aggregation_state[parent_task_id] = {
            "pending": pending,
            "results": {},
            "sender": original_sender
        }

    def _handle_subtask_completion(self, task_id: str, result: Any):
        # 上报完成
        self._report_event("finished", task_id, {"result": str(result)[:200]})  # 截断避免过大
        
        parent_id = self._get_parent_task_id(task_id)
        if parent_id in self._aggregation_state:
            state = self._aggregation_state[parent_id]
            state["results"][task_id] = result
            state["pending"].discard(task_id)
            if not state["pending"]:
                final = ResultAggregator.aggregate_sequential(state["results"])
                self.send(state["sender"], SubtaskResultMessage(parent_id, final))
                del self._aggregation_state[parent_id]

    def _handle_subtask_error(self, task_id: str, error: str):
        # 上报失败
        self._report_event("failed", task_id, {"error": str(error)[:200]})
        
        parent_id = self._get_parent_task_id(task_id)
        if parent_id in self._aggregation_state:
            del self._aggregation_state[parent_id]
        # 向上报告错误（简化）
        logger.error(f"Subtask {task_id} failed: {error}")

    def _handle_data_response(self, response: DataQueryResponse):
        req_id = response.request_id
        if req_id not in self._pending_data_requests:
            logger.warning(f"Orphaned data response: {req_id}")
            return

        info = self._pending_data_requests.pop(req_id)
        if "error" in response.result:
            self.send(info["sender"], SubtaskErrorMessage(info["task_id"], response.result["error"]))
            return

        # 构造增强上下文
        enhanced_context = {**info["context"], "db_result": response.result}

        try:
            result = self._execute_capability_fn(
                info["capability"], enhanced_context, info["memory"]
            )
            self.send(info["sender"], SubtaskResultMessage(info["task_id"], result))
        except Exception as e:
            self.send(info["sender"], SubtaskErrorMessage(info["task_id"], str(e)))

    def _get_parent_task_id(self, task_id: str) -> str:
        parts = task_id.rsplit(".", 1)
        return parts[0] if len(parts) > 1 else ""

    def _get_memory_actor(self):
        return self._registry.get_memory_actor()  # 全局单例 MemoryActor

    def _get_or_create_actor_ref(self, agent_id: str):
        if agent_id not in self._actor_ref_cache:
            ref = self.createActor(AgentActor)
            # 发送 init 消息（需从全局配置获取）
            # 此处简化：假设可通过 registry 获取 init 数据
            init_data = self._build_init_message_for(agent_id)
            self.send(ref, init_data)
            self._actor_ref_cache[agent_id] = ref
        return self._actor_ref_cache[agent_id]

    def _build_init_message_for(self, agent_id: str) -> dict:
        # 实际应从全局配置中心获取
        agent_info = self.registry.get_agent_by_id(agent_id)
        return {
            "type": "init",
            "agent_id": agent_id,
            "registry": self.registry,
            "orchestrator": self.orchestrator,
            "data_resolver": self.data_resolver,
            "neo4j_recorder": self._neo4j_recorder,
            "fetch_data_fn": self._fetch_data_fn,
            "acquire_resources_fn": self._acquire_resources_fn,
            "execute_capability_fn": self._execute_capability_fn,
            "execute_self_capability_fn": self._execute_self_capability_fn,
            "evaluator": self._evaluator,
            "improver": self._improver,
            "optimization_interval": self._optimization_interval,
        }

    def _run_optimization_cycle(self):
        try:
            tasks = []  # 你的优化任务生成逻辑
            for task in tasks:
                self._optimizer.run_optimization_task(
                    agent_id=self.agent_id,
                    is_leaf=self._is_leaf,
                    task=task,
                    memory=None  # Leaf 会在 optimizer 内部 snapshot
                )
        except Exception as e:
            logger.exception(f"Optimization cycle failed: {e}")

    def _process_optimization_queue(self):
        """处理优化队列"""
        pass

    def _report_event(self, event_type: str, task_id: str, details: Dict):
        """上报事件"""
        if self.orchestrator:
            self.orchestrator.report_event(event_type, task_id, details)

    def _fetch_data_for_task(self, task_id: str, query: str, capability: str, context: Dict, memory: Dict, sender):
        """为任务获取数据"""
        request_id = f"{task_id}_data"
        self._pending_data_requests[request_id] = {
            "task_id": task_id,
            "capability": capability,
            "context": context,
            "memory": memory,
            "sender": sender
        }
        
        if self._data_query_actor:
            # 发送数据查询请求
            pass

    # ==============================
    # 对外同步接口（保持兼容）
    # ==============================
    def fetch_data(self, query: str) -> Any:
        """数据库查询：同步调用，由外部注入"""
        return self._fetch_data_fn(query) if self._fetch_data_fn else None

    def acquire_resources(self, purpose: str) -> int:
        return self._acquire_resources_fn(purpose) if self._acquire_resources_fn else 0

    def wake_up_in(self, seconds):
        """模拟wake_up_in方法"""
        # 在实际实现中，这会调用Thespian的相关方法
        return None

