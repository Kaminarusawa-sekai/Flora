from typing import List, Optional, Any, Literal
from pydantic import Field, field_validator, ConfigDict

from .base_message import BaseMessage, TaskMessage
from .types import MessageType
from thespian.actors import ActorAddress

class UserRequestMessage(TaskMessage):
    message_type: Literal[MessageType.USER_REQUEST] = MessageType.USER_REQUEST
    user_id: str
    content: str


class InitConfigMessage(BaseMessage):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    backend_addr: ActorAddress
    message_type: Literal[MessageType.INIT_CONFIG] = MessageType.INIT_CONFIG
    backend_addr: ActorAddress



class TaskPausedMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_PAUSED] = MessageType.TASK_PAUSED
    missing_params: List[str]
    question: str


class TaskResultMessage(TaskMessage):
    message_type: Literal[MessageType.TASK_RESULT] = MessageType.TASK_RESULT
    result: Optional[Any] = None
    error: Optional[str] = None
    message: Optional[str] = None
