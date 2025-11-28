from datetime import datetime
from typing import Dict, Optional, Any, List
from enum import Enum

class TaskType(str, Enum):
    ONE_TIME = "one_time"
    LOOP = "loop"

class TaskStatus(str, Enum):
    CREATED = "created"
    SCHEDULED = "scheduled"      # Only for loop tasks
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"
    ARCHIVED = "archived"

class ScheduleConfig:
    """Schedule configuration for recurring tasks"""
    def __init__(
        self,
        cron: Optional[str] = None,  # e.g., "0 9 * * 1" for every Monday 9 AM
        interval_seconds: Optional[int] = None,  # e.g., 3600 for every hour
        next_run: Optional[datetime] = None
    ):
        self.cron = cron
        self.interval_seconds = interval_seconds
        self.next_run = next_run
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cron": self.cron,
            "interval_seconds": self.interval_seconds,
            "next_run": self.next_run.isoformat() if self.next_run else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScheduleConfig":
        return cls(
            cron=data.get("cron"),
            interval_seconds=data.get("interval_seconds"),
            next_run=datetime.fromisoformat(data["next_run"]) if data.get("next_run") else None
        )

class Task:
    """Task data transfer object"""
    def __init__(
        self,
        task_id: str,
        description: str,
        task_type: TaskType,
        created_at: Optional[datetime] = None,
        status: TaskStatus = TaskStatus.CREATED,
        result: Optional[Any] = None,
        schedule: Optional[ScheduleConfig] = None,
        next_run_time: Optional[datetime] = None,
        last_run_time: Optional[datetime] = None,
        comments: Optional[List[Dict]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        original_task_id: Optional[str] = None,  # For re-run tracking
        user_id: Optional[str] = None,           # User ID
        goal: Optional[str] = None,              # Task goal
        original_input: Optional[str] = None,    # Original user input
        subtasks: Optional[List[Dict]] = None,   # Subtasks
        execution_context_snapshot: Optional[str] = None,  # Execution context snapshot
        memory_ids: Optional[List[str]] = None,  # Associated memory IDs
        corrected_result: Optional[str] = None,  # Corrected result
    ):
        self.task_id = task_id
        self.description = description
        self.type = task_type
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = self.created_at  # Update time
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
            "schedule": self.schedule.to_dict() if self.schedule else None,
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
            schedule=ScheduleConfig.from_dict(data["schedule"]) if data.get("schedule") else None,
            next_run_time=datetime.fromisoformat(data["next_run_time"]) if data.get("next_run_time") else None,
            last_run_time=datetime.fromisoformat(data["last_run_time"]) if data.get("last_run_time") else None,
            comments=data.get("comments", []),
            metadata=data.get("metadata", {}),
            original_task_id=data.get("original_task_id"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
            user_id=data.get("user_id"),
            goal=data.get("goal"),
            original_input=data.get("original_input"),
            subtasks=data.get("subtasks", []),
            execution_context_snapshot=data.get("execution_context_snapshot"),
            memory_ids=data.get("memory_ids", []),
            corrected_result=data.get("corrected_result"),
        )
