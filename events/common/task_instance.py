from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .enums import ActorType, ScheduleType, TaskInstanceStatus


class TaskInstance(BaseModel):
    id: str
    trace_id: str
    parent_id: Optional[str] = None
    job_id: str

    actor_type: ActorType
    role: Optional[str] = None
    layer: int = 0
    is_leaf_agent: bool = False

    schedule_type: ScheduleType = ScheduleType.ONCE
    round_index: Optional[int] = None
    cron_trigger_time: Optional[datetime] = None

    status: TaskInstanceStatus
    node_path: str
    depth: int = 0
    depends_on: Optional[List[str]] = None

    split_count: int = 0
    completed_children: int = 0

    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_ref: Optional[str] = None
    error_msg: Optional[str] = None

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))