from typing import List, Optional, Dict
from datetime import datetime
from common.types.task import Task, TaskStatus, TaskType

class TaskRepository:
    """Task repository for storing and retrieving tasks"""
    def __init__(self):
        # In-memory storage (replace with actual database in production)
        self._task_store: Dict[str, Task] = {}  # task_id -> Task
        self._task_history: Dict[str, List[str]] = {}  # task_id -> [parent_task_id, ...] history tree
        self._user_task_index: Dict[str, List[str]] = {}  # user_id -> [task_id] user task index
    
    def create_task(self, task: Task) -> str:
        """Create a new task"""
        self._task_store[task.task_id] = task
        self._user_task_index.setdefault(task.user_id, []).append(task.task_id)
        
        # Record task history relationship
        if task.original_task_id:
            if task.original_task_id not in self._task_history:
                self._task_history[task.original_task_id] = []
            self._task_history[task.original_task_id].append(task.task_id)
        
        return task.task_id
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """Get task by ID"""
        return self._task_store.get(task_id)
    
    def list_user_tasks(self, user_id: str, status: Optional[TaskStatus] = None) -> List[Task]:
        """List tasks for a user"""
        ids = self._user_task_index.get(user_id, [])
        tasks = [self._task_store[tid] for tid in ids if tid in self._task_store]
        if status:
            tasks = [t for t in tasks if t.status == status]
        return sorted(tasks, key=lambda x: x.created_at, reverse=True)
    
    def update_task(self, task_id: str, updates: dict) -> bool:
        """Update task attributes"""
        if task_id not in self._task_store:
            return False
        
        task = self._task_store[task_id]
        for k, v in updates.items():
            if hasattr(task, k):
                setattr(task, k, v)
        task.updated_at = datetime.now()
        return True
    
    def add_comment(self, task_id: str, comment: str) -> bool:
        """Add comment to task"""
        if task_id not in self._task_store:
            return False
        
        self._task_store[task_id].comments.append({
            "content": comment,
            "created_at": datetime.now().isoformat()
        })
        self._task_store[task_id].updated_at = datetime.now()
        return True
    
    def get_task_history(self, task_id: str) -> List[Task]:
        """Get task history tree"""
        history = []
        
        # Find all descendant tasks recursively
        def find_descendants(current_id: str):
            if current_id in self._task_history:
                for child_id in self._task_history[current_id]:
                    if child_id in self._task_store:
                        history.append(self._task_store[child_id])
                        find_descendants(child_id)
        
        # Add current task first
        if task_id in self._task_store:
            history.append(self._task_store[task_id])
            # Find all descendants
            find_descendants(task_id)
        
        return history
    
    def find_task_by_reference(self, user_id: str, reference: str) -> Optional[Task]:
        """Find task by natural language reference"""
        tasks = self.list_user_tasks(user_id)
        if not tasks:
            return None
        
        # Strategy 1: Exact task_id match
        if reference in self._task_store:
            return self._task_store[reference]
        
        # Strategy 2: Keyword matching
        ref_lower = reference.lower()
        for task in tasks:
            desc = task.description.lower()
            goal = task.goal.lower()
            if ref_lower in desc or ref_lower in goal:
                return task
        
        # Strategy 3: Return latest task for "刚才那个" references
        if any(keyword in reference for keyword in ["刚才", "上一个", "那个"]):
            return tasks[0]
        
        return None
