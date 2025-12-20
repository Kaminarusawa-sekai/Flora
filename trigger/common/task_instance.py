from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime


class TaskInstance(BaseModel):
    """任务实例的Pydantic模型"""
    id: str
    definition_id: str
    trace_id: str
    status: str = "PENDING"  # PENDING, RUNNING, SUCCESS, FAILED
    schedule_type: str = "ONCE"  # CRON, LOOP, ONCE
    round_index: int = 0
    input_params: Dict = {}
    output_ref: Optional[str] = None
    error_msg: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    depends_on: List[str] = []
    
    class Config:
        from_attributes = True
