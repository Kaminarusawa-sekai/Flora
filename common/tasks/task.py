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
        self.created_at = created_at or datetime.now(timezone.utc)
        self.updated_at = self.created_at  # 添加更新时间字段
        self.status = status
        self.result = result
        self.schedule = schedule
        self.next_run_time = next_run_time
        self.last_run_time = last_run_time
        self.comments = comments or []
        self.metadata = metadata or {}
        self.original_task_id = original_task_id
        self.user_id = user_id
        self.goal = goal or description
        self.original_input = original_input or description
        self.subtasks = subtasks or []
        self.execution_context_snapshot = execution_context_snapshot
        self.memory_ids = memory_ids or []
        self.corrected_result = corrected_result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "type": self.type.value,
            "status": self.status.value,
            "result": self.result,
            "schedule": self.schedule,
            "next_run_time": self.next_run_time.isoformat() if self.next_run_time else None,
            "last_run_time": self.last_run_time.isoformat() if self.last_run_time else None,
            "comments": self.comments,
            "metadata": self.metadata,
            "original_task_id": self.original_task_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "user_id": self.user_id,
            "goal": self.goal,
            "original_input": self.original_input,
            "subtasks": self.subtasks,
            "execution_context_snapshot": self.execution_context_snapshot,
            "memory_ids": self.memory_ids,
            "corrected_result": self.corrected_result,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Task":
        return cls(
            task_id=data["task_id"],
            description=data["description"],
            task_type=TaskType(data["type"]),
            status=TaskStatus(data["status"]),
            result=data.get("result"),
            schedule=data.get("schedule"),
            next_run_time=datetime.fromisoformat(data["next_run_time"]) if data.get("next_run_time") else None,
            last_run_time=datetime.fromisoformat(data["last_run_time"]) if data.get("last_run_time") else None,
            comments=data.get("comments", []),
            metadata=data.get("metadata", {}),
            original_task_id=data.get("original_task_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc),
            user_id=data.get("user_id"),
            goal=data.get("goal"),
            original_input=data.get("original_input"),
            subtasks=data.get("subtasks", []),
            execution_context_snapshot=data.get("execution_context_snapshot"),
            memory_ids=data.get("memory_ids", []),
            corrected_result=data.get("corrected_result"),
        )