from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .enums import ActorType, ScheduleType


class TaskDefinition(BaseModel):
    id: str = Field(..., description="任务定义唯一ID")
    name: str
    actor_type: ActorType
    role: Optional[str] = None
    code_ref: str = Field(..., description="如 docker://my/agent:v1")
    entrypoint: str = "main.run"

    schedule_type: ScheduleType = ScheduleType.ONCE
    cron_expr: Optional[str] = None
    loop_config: Optional[Dict[str, Any]] = None

    resource_profile: str = "default"
    strategy_tags: List[str] = Field(default_factory=list)

    default_params: Dict[str, Any] = Field(default_factory=dict)
    timeout_sec: int = 300
    max_retries: int = 3
    is_active: bool = True
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))