from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum

from .enums import ScheduleType


class TaskDefinition(BaseModel):
    """任务定义的Pydantic模型 - 扩展版"""
    id: str
    name: str
    content: Dict[str, Any] = Field(default_factory=dict)  # 任务内容/逻辑定义
    cron_expr: Optional[str] = None
    schedule_type: ScheduleType = ScheduleType.IMMEDIATE
    schedule_config: Dict[str, Any] = Field(default_factory=dict)  # 调度配置
    loop_config: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    last_triggered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_temporary: bool = False  # 是否为临时定义
    
    class Config:
        from_attributes = True
