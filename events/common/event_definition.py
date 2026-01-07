from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
from .enums import ActorType, ScheduleType, NodeType


class EventDefinition(BaseModel):
    id: str = Field(..., description="事件定义唯一ID")
    name: str
    user_id: str = Field(..., description="用户ID")
    
    # 核心字段：决定了前端怎么渲染，以及后端怎么处理超时/重试
    node_type: NodeType
    
    # 原有字段
    actor_type: ActorType
    role: Optional[str] = None
    
    is_active: bool = True
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))