from datetime import datetime, timezone
from typing import Dict, Optional, Any
import uuid
from pydantic import BaseModel, Field, ConfigDict
from .event_type import EventType

class Event(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: EventType
    timestamp: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))

    # 关联任务信息（来自 TaskMessage）
    trace_id: str
    task_id: str
    task_path: str
    user_id: Optional[str] = None

    # 消息类型（可选，用于过滤）
    message_type: Optional[str] = None

    # 事件具体内容（结构化）
    payload: Dict[str, Any] = Field(default_factory=dict)

    # 可选：快照关键上下文（按需记录，避免过大）
    enriched_context_snapshot: Optional[Dict[str, Any]] = None  # 注意：只存值，不存 ContextEntry 对象

    # 错误信息（如果适用）
    error: Optional[str] = None