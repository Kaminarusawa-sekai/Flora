"""任务相关消息定义（Pydantic v2 + MessageType 枚举）"""
from typing import Literal, Dict, Any, List, Optional
from pydantic import Field

from .base_message import  TaskMessage
from .types import MessageType
from tasks.common.tasks.task_spec import TaskSpec

from thespian.actors import ActorAddress
# === 前台消息创建 ===
# 已移至 front_messages.py





# === 任务调度与分发 ===

class MCPTaskRequestMessage(TaskMessage):
    message_type: Literal[MessageType.MCP] = MessageType.MCP
    step: int
    description: str
    params: Dict[str, Any]
    executor: Optional[str] = None

    def is_dynamic_dispatch(self) -> bool:
        return self.executor is None or self.executor == ""



class TaskGroupRequestMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_GROUP_REQUEST] = MessageType.TASK_GROUP_REQUEST
    parent_task_id: str
    subtasks: List[TaskSpec]
    strategy: str = 'standard'
    original_sender: Optional[ActorAddress] = None


class ParallelTaskRequestMessage(TaskMessage):
    message_type: Literal[MessageType.PARALLEL_TASK_REQUEST] = MessageType.PARALLEL_TASK_REQUEST
    spec: TaskSpec


class ResultAggregatorTaskRequestMessage(TaskMessage):
    message_type: Literal[MessageType.RESULT_AGGREGATOR_REQUEST] = MessageType.RESULT_AGGREGATOR_REQUEST
    params: Dict[str, Any]
    spec: TaskSpec





# === 批量/组合结果 ===



class ExecuteTaskMessage(TaskMessage):
    message_type: Literal[MessageType.EXECUTE_TASK] = Field(default=MessageType.EXECUTE_TASK)
    capability: str  # e.g., "dify"
    params: Dict[str, Any]
    sender: str


class ExecutionResultMessage(TaskMessage):
    """执行结果消息"""
    message_type: Literal[MessageType.EXECUTION_RESULT] = Field(default=MessageType.EXECUTION_RESULT)
    status: Literal["SUCCESS", "FAILED", "NEED_INPUT"]
    result: Any
    error: Optional[str] = None
    agent_id: Optional[str] = None
    missing_params: Optional[List[str]] = None  # 当status为NEED_INPUT时使用





# === 任务结果 ===

class TaskCompletedMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_COMPLETED] = MessageType.TASK_COMPLETED
    result: Any
    status: Literal["SUCCESS", "FAILED", "ERROR", "CANCELLED","PAUSED","PENDING","NEED_INPUT"]
    agent_id: Optional[str] = None



