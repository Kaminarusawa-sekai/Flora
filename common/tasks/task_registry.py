# services/task_registry.py
import json
from typing import List, Optional, Dict
from datetime import datetime
from .task import Task
from .task_status import TaskStatus
from .task_type import TaskType

# 简化：使用内存字典，实际应使用数据库（如 SQLite / PostgreSQL）
_TASK_STORE: Dict[str, Task] = {}  # 任务存储
_TASK_HISTORY: Dict[str, List[str]] = {}  # task_id -> [parent_task_id, ...] 历史树结构
_USER_TASK_INDEX: Dict[str, List[str]] = {}  # user_id -> [task_id] 用户任务索引

class TaskRegistry:
    @staticmethod
    def create_task(task: Task) -> str:
        _TASK_STORE[task.id] = task
        _USER_TASK_INDEX.setdefault(task.user_id, []).append(task.id)
        
        # 记录任务历史关系
        if task.original_task_id:
            # 新任务是基于现有任务创建的，建立历史关系
            if task.original_task_id not in _TASK_HISTORY:
                _TASK_HISTORY[task.original_task_id] = []
            _TASK_HISTORY[task.original_task_id].append(task.id)
        
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
        _TASK_STORE[task_id].comments.append({
            "content": comment,
            "created_at": datetime.now().isoformat()
        })
        _TASK_STORE[task_id].updated_at = datetime.now()
        return True

    @staticmethod
    def get_task_history(task_id: str) -> List[Task]:
        """
        获取任务的历史树，包括所有祖先和后代任务
        """
        history = []
        
        # 查找所有后代任务（递归）
        def find_descendants(current_id: str):
            if current_id in _TASK_HISTORY:
                for child_id in _TASK_HISTORY[current_id]:
                    if child_id in _TASK_STORE:
                        history.append(_TASK_STORE[child_id])
                        find_descendants(child_id)
        
        # 先添加当前任务
        if task_id in _TASK_STORE:
            history.append(_TASK_STORE[task_id])
            # 查找所有后代
            find_descendants(task_id)
        
        return history

    @staticmethod
    def find_task_by_reference(user_id: str, reference: str) -> Optional[Task]:
        """
        根据用户的自然语言引用查找任务
        """
        tasks = TaskRegistry.list_user_tasks(user_id)
        if not tasks:
            return None
        
        # 策略1：精确匹配 task_id
        if reference in _TASK_STORE:
            return _TASK_STORE[reference]
        
        # 策略2：关键词匹配
        ref_lower = reference.lower()
        for task in tasks:
            desc = task.description.lower()
            goal = task.goal.lower()
            if ref_lower in desc or ref_lower in goal:
                return task
        
        # 策略3：默认返回最新任务（“刚才那个”）
        if any(keyword in reference for keyword in ["刚才", "上一个", "那个"]):
            return tasks[0]
        
        return None

    # 增强：通过自然语言模糊查找任务（简化版）
    @staticmethod
    def find_task_by_description(user_id: str, query: str) -> Optional[Task]:
        tasks = TaskRegistry.list_user_tasks(user_id)
        # 简单关键词匹配（实际可用 embedding 相似度）
        for task in tasks:
            if query.lower() in task.goal.lower() or query.lower() in task.original_input.lower():
                return task
        return None