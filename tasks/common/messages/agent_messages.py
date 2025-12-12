"""Agent 相关消息（Pydantic v2 风格）"""
from typing import Literal, Dict, Any, List, Optional
from pydantic import Field, ConfigDict
from thespian.actors import ActorAddress
from .base_message import BaseMessage
from .types import MessageType



# === Agent 执行 ===

class AgentTaskMessage(BaseMessage):
    """Agent任务消息"""
    agent_id: str

     # 可选上下文（仅当来自任务执行流时存在）
    task_id: Optional[str] = None
    trace_id: Optional[str] = None
    task_path: Optional[str] = None
    
    model_config = ConfigDict(arbitrary_types_allowed=True)
    message_type: Literal[MessageType.AGENT_TASK] = MessageType.AGENT_TASK
    task_id: str
    content: str
    description: Optional[str] = None
    context: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"
    reply_to: Optional[ActorAddress] = None
    is_parameter_completion: bool = False
    parameters: Dict[str, Any] = Field(default_factory=dict)


class ResumeTaskMessage(BaseMessage):
    """恢复任务消息"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    message_type: Literal["resume_task"] = "resume_task"
    task_id: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default_user"
    reply_to: Optional[ActorAddress] = None





