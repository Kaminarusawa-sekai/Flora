from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel


class TaskStatusEvent(BaseModel):
    """任务状态变更事件"""
    task_id: str
    trace_id: str
    status: str
    timestamp: datetime
    output_ref: Optional[str] = None
    error_msg: Optional[str] = None


class TraceCancelledEvent(BaseModel):
    """Trace 取消事件"""
    trace_id: str
    timestamp: datetime
    reason: Optional[str] = None


class LoopRoundStartedEvent(BaseModel):
    """LOOP 轮次开始事件"""
    task_id: str
    trace_id: str
    round_index: int
    timestamp: datetime


class TaskStartedEvent(BaseModel):
    """任务开始执行事件"""
    task_id: str
    trace_id: str
    worker_id: Optional[str] = None
    timestamp: datetime


class TaskFailedEvent(BaseModel):
    """任务执行失败事件"""
    task_id: str
    trace_id: str
    error_msg: str
    timestamp: datetime


class TaskCompletedEvent(BaseModel):
    """任务执行成功事件"""
    task_id: str
    trace_id: str
    output_ref: str
    timestamp: datetime