from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

from events.common.actor_dto import ActorType


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"


class TaskScheduleType(str, Enum):
    """任务调度类型枚举"""
    ONCE = "ONCE"
    CRON = "CRON"
    LOOP = "LOOP"


class ControlEventType(str, Enum):
    """控制事件类型枚举"""
    CANCEL = "CANCEL"
    PAUSE = "PAUSE"
    RESUME = "RESUME"


class TaskEvent(BaseModel):
    """任务事件模型"""
    event_id: str
    task_id: str
    trace_id: str
    parent_id: Optional[str] = None
    event_type: str
    status: TaskStatus
    timestamp: datetime
    error_info: Optional[Dict[str, Any]] = None
    result: Optional[Any] = None


class ControlEvent(BaseModel):
    """控制事件模型"""
    event_id: str
    trace_id: str
    task_id: Optional[str] = None
    event_type: ControlEventType
    timestamp: datetime
    issuer: str
    reason: Optional[str] = None


class TaskDefinition(BaseModel):
    """任务定义模型"""
    id: str
    name: str
    description: Optional[str] = None
    schedule_type: TaskScheduleType = TaskScheduleType.ONCE
    cron_expr: Optional[str] = None
    loop_config: Optional[Dict[str, Any]] = None
    priority: int = 50
    max_retries: int = 0
    resource_profile: str = "default"
    strategy_tags: List[str] = Field(default_factory=list)
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskInstance(BaseModel):
    """任务实例模型"""
    id: str
    definition_id: str
    trace_id: str
    parent_id: Optional[str] = None
    actor_type: ActorType
    actor_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    layer: Optional[int] = None
    depth: Optional[int] = None
    node_path: Optional[str] = None
    depends_on: Optional[List[str]] = None
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_result: Optional[Any] = None
    error_info: Optional[Dict[str, Any]] = None
    priority: int = 50
    resource_profile: str = "default"
    strategy_tags: List[str] = Field(default_factory=list)
    completed_children: int = 0
    split_count: int = 1
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    max_retries: int = 0
    retry_count: int = 0


class ScheduledRun(BaseModel):
    """定时运行记录模型"""
    id: str
    definition_id: str
    trace_id: str
    scheduled_at: datetime
    triggered_at: Optional[datetime] = None
    status: str  # SUCCESS / FAILED


class LoopRoundContext(BaseModel):
    """循环轮次上下文模型"""
    trace_id: str
    round_index: int
    input_params: Dict[str, Any]
    output_summary: Optional[Dict[str, Any]] = None
    should_continue: bool = True
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))
