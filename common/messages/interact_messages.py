from typing import List, Optional, Any, Literal
from pydantic import Field

from .base_message import BaseMessage, TaskMessage
from .types import MessageType


class UserRequestMessage(TaskMessage):
    message_type: Literal[MessageType.USER_REQUEST] = MessageType.USER_REQUEST
    user_id: str
    content: str


class InitConfigMessage(BaseMessage):
    message_type: Literal[MessageType.INIT_CONFIG] = MessageType.INIT_CONFIG
    backend_addr: str
    

class TaskPausedMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_PAUSED] = MessageType.TASK_PAUSED
    missing_params: List[str]
    question: str


class TaskResultMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_RESULT] = MessageType.TASK_RESULT
    result: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
