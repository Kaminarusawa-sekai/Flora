"""任务相关消息定义（Pydantic v2 + MessageType 枚举）"""
from typing import Literal, Dict, Any, List, Optional
from pydantic import Field

from .base_message import  TaskMessage
from .types import MessageType
from common.tasks.task_spec import TaskSpec


# === 前台消息创建 ===
# 已移至 front_messages.py






# === 任务调度与分发 ===

class MCPTaskRequestMessage(TaskMessage):
    message_type: Literal[MessageType.MCP] = MessageType.MCP
    step: int
    description: str
    params: Dict[str, Any]
    executor: Optional[str] = None
    reply_to: Optional[str] = None

    def is_dynamic_dispatch(self) -> bool:
        return self.executor is None or self.executor == ""



class TaskGroupRequestMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_GROUP_REQUEST] = MessageType.TASK_GROUP_REQUEST
    parent_task_id: str
    subtasks: List[TaskSpec]
    strategy: str = 'standard'
    original_sender: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    user_id: Optional[str] = None


class ParallelTaskRequestMessage(TaskMessage):
    message_type: Literal[MessageType.PARALLEL_TASK_REQUEST] = MessageType.PARALLEL_TASK_REQUEST
    spec: TaskSpec
    reply_to: str



# === 批量/组合结果 ===


class ExecuteTaskMessage(TaskMessage):
    message_type: Literal[MessageType.EXECUTE_TASK] = MessageType.EXECUTE_TASK
    spec: TaskSpec
    reply_to: str




# === 任务结果 ===

class TaskCompletedMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_COMPLETED] = MessageType.TASK_COMPLETED
    result: Any
    status: Literal["SUCCESS", "FAILED", "ERROR", "CANCELLED","PAUSED","PENDING","NEED_INPUT"]
    agent_id: Optional[str] = None



