# agent/messages.py
from typing import Optional, Any, Dict,ClassVar,List
from dataclasses import dataclass, asdict
from enum import Enum
from thespian.actors import ActorAddress

# --- 消息类型枚举 ---
class MessageType(Enum):
    INIT = "init"
    TASK = "task"
    SUBTASK_RESULT = "subtask_result"
    SUBTASK_ERROR = "subtask_error"
    MEMORY_RESPONSE = "memory_response"
    OPTIMIZATION_WAKEUP = "optimization_wakeup"
    DATA_QUERY_RESPONSE = "data_query_response"
    SWARM_TASK = "swarm_task"
    SWARM_RESULT = "swarm_result"
    SWARM_ERROR = "swarm_error"
    DATA_QUERY_REQUEST = "data_query_request"
    ROUTE_DATA_QUERY = "route_data_query"
    DATA_SOURCE_FOUND = "data_source_found"
    DATA_SOURCE_NOT_FOUND = "data_source_not_found"
    DifySchemaRequest = "dify_schema_request"
    DifySchemaResponse = "dify_schema_response"
    DifyExecuteRequest = "dify_execute_request"
    DifyExecuteResponse = "dify_execute_response"
    MCP_FALLBACK_REQUEST = "mcp_fallback_request"
    # 新增：内存相关消息
    LOAD_MEMORY_FOR_AGENT = "load_memory_for_agent"
    INGEST_MEMORY = "ingest_memory"
    BUILD_CONTEXT_FOR_LLM = "build_context_for_llm"
    MEMORY_ERROR = "memory_error"


# --- 基类：所有消息的父类 ---
@dataclass
class BaseMessage:
    # 自动推断 message_type，子类可覆盖（但通常不需要）
    message_type: ClassVar[MessageType]  # type: ignore

    def __post_init__(self):
        # 自动设置 message_type 为子类对应的枚举值（约定：类名转为 snake_case）
        if self.message_type is None:
            class_name = self.__class__.__name__
            # 将类名转为 snake_case 并匹配 MessageType
            snake_name = self._to_snake_case(class_name)
            try:
                self.message_type = MessageType(snake_name)
            except ValueError:
                raise ValueError(f"MessageType enum missing for class: {class_name}")

    @staticmethod
    def _to_snake_case(name: str) -> str:
        # 简单转换：TaskMessage -> task_message
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

    def to_dict(self) -> Dict[str, Any]:
        """统一输出为字典（不含 message_type 重复？其实可以保留）"""
        return asdict(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.to_dict()})"


# --- 具体消息类（全部继承 BaseMessage）---

@dataclass
class InitMessage(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.INIT
    agent_id: str
    capabilities: str
    memory_key: Optional[str] = None
    optimization_interval: int = 3600
    registry: Any = None
    orchestrator: Any = None
    data_resolver: Any = None
    neo4j_recorder: Any = None
    fetch_data_fn: Any = None
    acquire_resources_fn: Any = None
    evaluator: Any = None
    improver: Any = None

    def __post_init__(self):
        if self.memory_key is None:
            self.memory_key = self.agent_id
        super().__post_init__()


@dataclass
class TaskMessage(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.TASK
    task_id: str
    context: Dict[str, Any]


@dataclass
class SubtaskResultMessage(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.SUBTASK_RESULT
    task_id: str
    result: Any


@dataclass
class SubtaskErrorMessage(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.SUBTASK_ERROR
    task_id: str
    error: str


@dataclass
class MemoryResponse(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.MEMORY_RESPONSE
    key: str
    value: Any


@dataclass
class DataQueryResponse(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DATA_QUERY_RESPONSE
    request_id: str
    result: Any
    error: Optional[str] = None


@dataclass
class SwarmTaskMessage(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.SWARM_TASK
    swarm_id: str
    variant_id: str
    capability: str
    context: Dict[str, Any]


@dataclass
class SwarmResultMessage(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.SWARM_RESULT
    swarm_id: str
    variant_id: str
    result: Any


@dataclass
class SwarmErrorMessage(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.SWARM_ERROR
    swarm_id: str
    variant_id: str
    error: str


@dataclass
class InitDataQueryActor(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DATA_QUERY_REQUEST
    agent_id: str


@dataclass
class DataQueryRequest(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DATA_QUERY_REQUEST
    request_id: str
    query: str
    agent_id: str


# --- 路由相关消息（也可放 routing_messages.py，但继承 BaseMessage）---
@dataclass
class RouteDataQuery(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.ROUTE_DATA_QUERY
    start_agent_id: str
    requester: ActorAddress


@dataclass
class DataSourceFound(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DATA_SOURCE_FOUND
    data_actor_addr: ActorAddress


@dataclass
class DataSourceNotFound(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DATA_SOURCE_NOT_FOUND
    reason: str = ""


# --- 特殊标记类（无字段，但也要类型）---
@dataclass
class WakeupMessage(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.OPTIMIZATION_WAKEUP
    pass


@dataclass
class OptimizationWakeup(WakeupMessage):
    
    pass  # 自动继承 message_type = MessageType.OPTIMIZATION_WAKEUP


@dataclass
class DifySchemaRequest(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DifySchemaRequest
    task_id: str
    echo_payload: Dict[str, Any]
    api_key: str          # ← 新增
    base_url: str         # ← 新增


@dataclass
class DifySchemaResponse(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DifySchemaResponse  # ← 修正！
    task_id: str
    input_schema: List[Dict[str, Any]]
    echo_payload: Dict[str, Any]
    error: Optional[str] = None


@dataclass
class DifyExecuteRequest(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DifyExecuteRequest
    task_id: str
    inputs: Dict[str, Any]
    user: str
    original_sender: Any
    api_key: str          # ← 新增
    base_url: str         # ← 新增

@dataclass
class DifyExecuteResponse(BaseMessage):
    message_type: ClassVar[MessageType] = MessageType.DifyExecuteResponse
    task_id: str
    outputs: Dict[str, Any]
    workflow_run_id: str
    status: str
    original_sender: Any
    error: Optional[str] = None



@dataclass
class McpFallbackRequest(BaseMessage):
    """MCP Actor 接收的任务请求消息"""
    message_type: ClassVar[MessageType]  = MessageType.MCP_FALLBACK_REQUEST
    task_id: str
    context: Dict[str, Any]
    


@dataclass
class LoadMemoryForAgent(BaseMessage):
    message_type: ClassVar[MessageType]  = MessageType.LOAD_MEMORY_FOR_AGENT
    user_id: str          # 👈 用户 ID（用于 UnifiedMemoryManager）
    agent_id: str         # 👈 Agent ID（用于日志、追踪、多 agent 场景）

@dataclass
class IngestMemory(BaseMessage):
    message_type: ClassVar[MessageType]  = MessageType.INGEST_MEMORY
    content: str
    role: str = "user"

@dataclass
class BuildContextForLLM(BaseMessage):
    message_type: ClassVar[MessageType]  = MessageType.BUILD_CONTEXT_FOR_LLM
    query: Optional[str] = None

@dataclass
class MemoryResponse(BaseMessage):
    message_type: ClassVar[MessageType]  = MessageType.MEMORY_RESPONSE
    request_type: str    # e.g., "context", "ingest"
    payload: Any

@dataclass
class MemoryError(BaseMessage):
    message_type: ClassVar[MessageType]  = MessageType.MEMORY_ERROR
    message: str