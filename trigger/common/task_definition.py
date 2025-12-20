from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


class TaskDefinition(BaseModel):
    """任务定义的Pydantic模型"""
    id: str
    name: str
    cron_expr: Optional[str] = None
    is_active: bool = True
    loop_config: Dict = {}
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True
