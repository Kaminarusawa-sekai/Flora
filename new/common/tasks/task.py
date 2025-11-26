from datetime import datetime
from typing import Dict, Optional, Any, List
from .task_type import TaskType
from .task_status import TaskStatus

##TODO:在task里加上task和新增字段，这样子保障一部分智能体生成的任务能直接执行，优化执行速度

class Task:
    def __init__(
        self,
        task_id: str,
        description: str,
        task_type: TaskType,
        created_at: Optional[datetime] = None,
        status: TaskStatus = TaskStatus.CREATED,
        result: Optional[Any] = None,
        schedule: Optional[str] = None,          # cron 或 interval_sec
        next_run_time: Optional[datetime] = None,
        last_run_time: Optional[datetime] = None,
        comments: Optional[List[Dict]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        original_task_id: Optional[str] = None,  # 用于 re-run 追踪
        user_id: Optional[str] = None,           # 添加用户ID字段
        goal: Optional[str] = None,              # 添加目标字段
        original_input: Optional[str] = None,    # 添加原始输入字段
        subtasks: Optional[List[Dict]] = None,   # 添加子任务字段
        execution_context_snapshot: Optional[str] = None,  # 添加执行上下文快照
        memory_ids: Optional[List[str]] = None,  # 添加关联记忆ID
        corrected_result: Optional[str] = None,  # 添加修正结果字段
    ):
        self.task_id = task_id
        self.description = description
        self.type = task_type
