# agent/messages.py
from typing import List, Optional,Any, Dict
import logging
logger = logging.getLogger(__name__)
from enum import Enum

class InitMessage:
    def __init__(
        self,
        agent_id: str,
        capabilities: str,           # Leaf: ["book_flight"]; Branch: ["route_flight"]
        # dispatch_rules: Optional[dict] = None,  # Branch 专用：从 Neo4j 加载的路由规则
        memory_key: Optional[str] = None,       # 默认 = agent_id
        optimization_interval: int = 3600,
        # 依赖注入
        registry=None,
        orchestrator=None,
        data_resolver=None,
        neo4j_recorder=None,
        fetch_data_fn=None,
        acquire_resources_fn=None,
        evaluator=None,
        improver=None,
    ):
        self.agent_id = agent_id
   
        self.capabilities = capabilities

        self.memory_key = memory_key or agent_id
        self.optimization_interval = optimization_interval

        # 依赖
        self.registry = registry
        self.orchestrator = orchestrator
        self.data_resolver = data_resolver
        self.neo4j_recorder = neo4j_recorder
        self.fetch_data_fn = fetch_data_fn
        self.acquire_resources_fn = acquire_resources_fn
        self.evaluator = evaluator
        self.improver = improver

class TaskMessage:
    def __init__(self, task_id: str, capability: str, context: Dict):
        self.task_id = task_id
        self.capability = capability
        self.context = context

class SubtaskResultMessage:
    def __init__(self, task_id: str, result: Any):
        self.task_id = task_id
        self.result = result

class SubtaskErrorMessage:
    def __init__(self, task_id: str, error: str):
        self.task_id = task_id
        self.error = error

class MemoryResponse:
    def __init__(self, key: str, value: Any):
        self.key = key
        self.value = value

class OptimizationWakeup:
    pass

class DataQueryResponse:
    def __init__(self, request_id: str, result: Any):
        self.request_id = request_id
        self.result = result

class WakeupMessage:
    pass


# --- 消息定义（保持你原有的）---
class OptimizationWakeup(WakeupMessage): pass

class TaskMessage:
    def __init__(self, task_id: str, context: Dict[str, Any]):
        self.task_id = task_id

        self.context = context

class SubtaskResultMessage:
    def __init__(self, task_id: str, result: Any):
        self.task_id = task_id
        self.result = result

class SubtaskErrorMessage:
    def __init__(self, task_id: str, error: str):
        self.task_id = task_id
        self.error = error

# ... 其他消息（SwarmXXX 等）保持不变 ...


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

class InitDataQueryActor:
    agent_id: str


class DataQueryRequest:
    request_id: str
    query: str
    agent_id: str  # ✅ 新增：用于加载对应记忆



# routing_messages.py
from thespian.actors import ActorAddress


class RouteDataQuery:
    def __init__(self, start_agent_id: str, requester: ActorAddress):
        self.start_agent_id = start_agent_id  # e.g., "Sales_East"
        self.requester = requester

class DataSourceFound:
    def __init__(self, data_actor_addr: ActorAddress):
        self.data_actor_addr = data_actor_addr

class DataSourceNotFound:
    def __init__(self, reason: str = ""):
        self.reason = reason


class MessageType(Enum):
    INIT = "init"
    TASK = "task"
    SUBTASK_RESULT = "subtask_result"
    SUBTASK_ERROR = "subtask_error"
    MEMORY_RESPONSE = "memory_response"
    OPTIMIZATION_WAKEUP = "optimization_wakeup"
    DATA_QUERY_RESPONSE = "data_query_response"