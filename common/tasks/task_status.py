from enum import Enum

class TaskStatus(str, Enum):
    CREATED = "created"
    SCHEDULED = "scheduled"      # 仅 loop 任务使用
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    ARCHIVED = "archived"