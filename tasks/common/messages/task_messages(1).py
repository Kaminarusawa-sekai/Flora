"""任务相关消息定义（Pydantic v2 + MessageType 枚举）"""
from typing import Literal, Dict, Any, List, Optional
from pydantic import Field, ConfigDict

from .base_message import  BaseMessage
from .types import MessageType
from ..taskspec.task_spec import TaskSpec
from ..context.context_entry import ContextEntry

from thespian.actors import ActorAddress
import uuid


class TaskMessage(BaseMessage):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task_id: str=Field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str  # ← 全链路唯一根 ID
    task_path: str  # ← 如 "/0", "/0/2", "/0/2/1"


    content: str = Field(default="")
    description: str = Field(default="")
    # 【不变】全局上下文：从根任务一路透传，不可变
    global_context: Dict[str, Any] = Field(default_factory=dict)


    # 【动态】富上下文：不断累积的"可能有用"信息（关键！）
    enriched_context: Dict[str, ContextEntry] = Field(default_factory=dict)

    # 用户身份（用于权限/计费）
    user_id: Optional[str] = None

    # 回调地址（上一层 Actor）
    reply_to: Optional[ActorAddress] = None

    # 根回调地址（TaskRouter），用于 NEED_INPUT 等状态直接回报，整个链路不变
    root_reply_to: Optional[ActorAddress] = None

    def get_user_input(self) -> str:
        return "内容：" + str(self.content or "") + " 描述：" + str(self.description or "")

    def add_task_path(self, step: int) -> None:
        return self.task_path + f"/{step}"




class AgentTaskMessage(TaskMessage):
    """Agent任务消息"""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)

    message_type: Literal[MessageType.AGENT_TASK] = MessageType.AGENT_TASK

    agent_id: str

    is_parameter_completion: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ResumeTaskMessage(TaskMessage):
    """恢复任务消息"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    message_type: Literal["resume_task"] = "resume_task"
    task_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"
    reply_to: Optional[ActorAddress] = None




class TaskGroupRequestMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_GROUP_REQUEST] = MessageType.TASK_GROUP_REQUEST
    subtasks: List[TaskSpec]
    strategy: str = 'standard'




# === 任务调度与分发 ===

class MCPTaskRequestMessage(TaskMessage):
    message_type: Literal[MessageType.MCP] = MessageType.MCP
    step: int
    executor: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

    def is_dynamic_dispatch(self) -> bool:
        return self.executor is None or self.executor == ""



class ParallelTaskRequestMessage(TaskMessage):
    message_type: Literal[MessageType.PARALLEL_TASK_REQUEST] = MessageType.PARALLEL_TASK_REQUEST
    step: int
    spec: TaskSpec


class ResultAggregatorTaskRequestMessage(TaskMessage):
    message_type: Literal[MessageType.RESULT_AGGREGATOR_REQUEST] = MessageType.RESULT_AGGREGATOR_REQUEST
    step: int
    spec: TaskSpec





# === 批量/组合结果 ===



class ExecuteTaskMessage(TaskMessage):
    message_type: Literal[MessageType.EXECUTE_TASK] = Field(default=MessageType.EXECUTE_TASK)
    capability: str  # e.g., "dify"
    running_config: Optional[Dict[str, Any]] = None


class ExecutionResultMessage(TaskMessage):
    """执行结果消息"""
    message_type: Literal[MessageType.EXECUTION_RESULT] = Field(default=MessageType.EXECUTION_RESULT)
    status: Literal["SUCCESS", "FAILED", "NEED_INPUT"]
    result: Any
    error: Optional[str] = None
    missing_params: Optional[List[str]] = None  # 当status为NEED_INPUT时使用





# === 任务结果 ===

class TaskCompletedMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_COMPLETED] = MessageType.TASK_COMPLETED
    result: Any
    status: Literal["SUCCESS", "FAILED", "ERROR", "CANCELLED","PAUSED","PENDING","NEED_INPUT"]
    step: Optional[int] = None


