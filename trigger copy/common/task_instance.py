from pydantic import BaseModel, Field
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone


class TaskInstance(BaseModel):
    """
    任务实例的Pydantic模型 - 保持原样用于执行记录
    注意：ScheduledTask和TaskInstance可以合并，但为了兼容性我们分开
    """
    id: str
    definition_id: str
    trace_id: str
    status: str = "PENDING"  # PENDING, RUNNING, SUCCESS, FAILED
    schedule_type: str = "ONCE"  # CRON, LOOP, ONCE, DELAY, INTERVAL
    round_index: int = 0
    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_ref: Optional[str] = None
    error_msg: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    depends_on: List[str] = Field(default_factory=list)
    
    class Config:
        from_attributes = True
