# services/task_registry.py
import json
from typing import List, Optional
from datetime import datetime
from .models.task import Task, TaskStatus, TaskType

# 简化：使用内存字典，实际应使用数据库（如 SQLite / PostgreSQL）
_TASK_STORE: Dict[str, Task] = {}
_USER_TASK_INDEX: Dict[str, List[str]] = {}  # user_id -> [task_id]

class TaskRegistry:
    @staticmethod
    def create_task(task: Task) -> str:
        _TASK_STORE[task.id] = task
        _USER_TASK_INDEX.setdefault(task.user_id, []).append(task.id)
        return task.id

    @staticmethod
    def get_task(task_id: str) -> Optional[Task]:
        return _TASK_STORE.get(task_id)

    @staticmethod
    def list_user_tasks(user_id: str, status: Optional[TaskStatus] = None) -> List[Task]:
        ids = _USER_TASK_INDEX.get(user_id, [])
        tasks = [_TASK_STORE[tid] for tid in ids if tid in _TASK_STORE]
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda x: x.created_at, reverse=True)

    @staticmethod
    def update_task(task_id: str, updates: dict) -> bool:
        if task_id not in _TASK_STORE:
            return False
        task = _TASK_STORE[task_id]
        for k, v in updates.items():
            if hasattr(task, k):
                setattr(task, k, v)
        task.updated_at = datetime.now()
        return True

    @staticmethod
    def add_comment(task_id: str, comment: str) -> bool:
        if task_id not in _TASK_STORE:
            return False
        _TASK_STORE[task_id].comments.append(comment)
        _TASK_STORE[task_id].updated_at = datetime.now()
        return True

    # 增强：通过自然语言模糊查找任务（简化版）
    @staticmethod
    def find_task_by_description(user_id: str, query: str) -> Optional[Task]:
        tasks = TaskRegistry.list_user_tasks(user_id)
        # 简单关键词匹配（实际可用 embedding 相似度）
        for task in tasks:
            if query.lower() in task.goal.lower() or query.lower() in task.original_input.lower():
                return task
        return None