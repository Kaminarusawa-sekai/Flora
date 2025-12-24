from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from .enums import ScheduleType, TaskStatus


class ScheduledTask(BaseModel):
    """
    调度任务模型 - 用于调度表
    基于TaskInstance扩展，但专注于调度逻辑
    """
    id: str
    definition_id: str
    trace_id: str
    status: TaskStatus = TaskStatus.PENDING
    
    # 调度相关字段
    schedule_type: ScheduleType = ScheduleType.IMMEDIATE
    scheduled_time: datetime  # 计划执行时间
    execute_after: Optional[datetime] = None  # 实际执行时间（用于延迟任务）
    schedule_config: Dict[str, Any] = Field(default_factory=dict)  # 调度配置
    
    # 执行相关字段（保留原TaskInstance的字段）
    round_index: int = 0
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_ref: Optional[str] = None
    error_msg: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    depends_on: List[str] = Field(default_factory=list)
    
    # 新增调度字段
    priority: int = 0  # 优先级
    max_retries: int = 3  # 最大重试次数
    retry_count: int = 0  # 当前重试次数
    cancelled_at: Optional[datetime] = None
    external_status_pushed: bool = False  # 状态是否已推送到外部系统
    
    class Config:
        from_attributes = True
