from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4

# --- 枚举定义 ---
class IntentType(str, Enum):
    CREATE = "CREATE_TASK"
    MODIFY = "MODIFY_TASK"
    QUERY = "QUERY_TASK"
    DELETE = "DELETE_TASK"
    IDLE = "IDLE_CHAT"
    RESUME = "RESUME_INTERRUPTED"
    CANCEL = "CANCEL_TASK"
    PAUSE = "PAUSE_TASK"
    RESUME_TASK = "RESUME_TASK"
    RETRY = "RETRY_TASK"
    SET_SCHEDULE = "SET_SCHEDULE"

class SlotSource(str, Enum):
    USER = "USER"          # 用户明确输入
    DEFAULT = "DEFAULT"    # 系统默认值
    INFERENCE = "INFERENCE" # 历史推断/上下文继承
    CORRECTION = "CORRECTION" # 用户纠错

class ExecutionStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    RUNNING = "RUNNING"
    AWAITING_USER_INPUT = "AWAITING_USER_INPUT" # 等待用户介入（如验证码）
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ERROR = "ERROR"
    CANCELLED = "CANCELLED"

class ActionType(str, Enum):
    TEXT = "TEXT"
    CONFIRM = "CONFIRM"
    CANCEL = "CANCEL"
    RETRY = "RETRY"
    SELECT_OPTION = "SELECT_OPTION" # 列表选择

# --- 基础组件 ---
class ExecutionLogEntry(BaseModel):
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    level: str = "INFO"
    message: str

class TaskSummary(BaseModel):
    id: str
    title: str  # 用于展示，如 "爬取京东数据任务"
    type: str

class TaskStatusSummary(BaseModel):
    task_id: str
    status: str   # "RUNNING (50%)"
    progress: float = 0.0
    message: str = ""