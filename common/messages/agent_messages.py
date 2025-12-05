"""Agent 相关消息（Pydantic v2 风格）"""
from typing import Literal, Dict, Any, List, Optional
from pydantic import Field

from .base_message import BaseMessage
from .types import MessageType


class InitMessage(BaseMessage):
    """初始化消息"""
    message_type: Literal[MessageType.INIT] = MessageType.INIT
    agent_id: str
    capabilities: List[str]
    memory_key: str



# === Agent 执行 ===

class AgentTaskMessage(BaseMessage):
    """Agent任务消息"""
    message_type: Literal[MessageType.AGENT_TASK] = MessageType.AGENT_TASK
    task_id: str
    content: str
    description: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"
    reply_to: Optional[str] = None
    is_parameter_completion: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ResumeTaskMessage(BaseMessage):
    """恢复任务消息"""
    message_type: Literal["resume_task"] = "resume_task"
    task_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"
    reply_to: Optional[str] = None


class TaskPausedMessage(BaseMessage):
    """任务暂停消息"""
    message_type: Literal[MessageType.TASK_PAUSED] = MessageType.TASK_PAUSED
    task_id: str
    missing_params: List[str] = Field(default_factory=list)
    question: str = ""
    execution_actor_address: Optional[str] = None


