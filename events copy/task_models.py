from enum import Enum
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class TaskTriggerType(str, Enum):
    IMMEDIATE = "IMMEDIATE"   # 立即执行
    SCHEDULED = "SCHEDULED"   # 指定未来某时间点执行一次
    LOOP = "LOOP"             # 循环执行 (间隔/Cron)

class TaskStatus(str, Enum):
    ACTIVE = "ACTIVE"         # 调度中 (针对循环任务)
    PAUSED = "PAUSED"         # 调度暂停 (不触发新任务)
    RUNNING = "RUNNING"       # 实例正在运行
    COMPLETED = "COMPLETED"   # 结束
    CANCELLED = "CANCELLED"   # 取消

# 任务定义 (规则)
class TaskDefinition(BaseModel):
    task_def_id: str          # 规则ID (如: daily_report_001)
    user_id: str
    content: str              # 原始指令
    trigger_type: TaskTriggerType
    trigger_args: Optional[Dict[str, Any]] = None
    status: TaskStatus = TaskStatus.ACTIVE
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

# 任务实例 (执行)
class TaskInstance(BaseModel):
    instance_id: str          # 实例ID (如: task_def_id_timestamp)
    task_def_id: str          # 关联的任务定义ID
    content: str              # 执行的内容
    status: TaskStatus = TaskStatus.RUNNING
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None