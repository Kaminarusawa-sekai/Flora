from typing import Dict, List, Any
from datetime import datetime, timedelta
from events.command_tower.models import TaskInstance


class TaskObserver:
    """
    任务观察器
    提供内部查询能力，支撑监控、调试、前端可视化
    """
    
    def __init__(self, db_client):
        """
        初始化任务观察器
        
        Args:
            db_client: 数据库客户端，需支持相关查询方法
        """
        self.db = db_client
    
    def get_task_tree(self, trace_id: str) -> Dict[int, List[TaskInstance]]:
        """
        获取整棵任务树，按layer分组
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            按layer分组的任务实例字典，键为layer值，值为该layer的任务列表
        """
        tasks = self.db.get_tasks_by_trace_id(trace_id)
        
        # 按layer分组
        tree = {}
        for task in tasks:
            layer = task.layer or 0
            if layer not in tree:
                tree[layer] = []
            tree[layer].append(task)
        
        return tree
    
    def get_ancestors(self, task_id: str) -> List[TaskInstance]:
        """
        获取某节点的执行路径（从根到当前）
        
        Args:
            task_id: 任务ID
            
        Returns:
            从根任务到当前任务的祖先列表，顺序为根到当前
        """
        task = self.db.get_task(task_id)
        if not task:
            return []
        
        ancestors = []
        current = task
        
        # 向上遍历获取所有祖先
        while current:
            ancestors.append(current)
            if not current.parent_id:
                break
            current = self.db.get_task(current.parent_id)
        
        # 反转列表，使根任务在最前面
        return list(reversed(ancestors))
    
    def get_overall_progress(self, trace_id: str) -> float:
        """
        计算整体进度（简单计数方式）
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            整体进度，范围0.0-1.0
        """
        total = self.db.count_tasks(trace_id)
        completed = self.db.count_completed_tasks(trace_id)
        
        return completed / total if total else 0.0
    
    def find_hanging_tasks(self, timeout_hours: int = 1) -> List[TaskInstance]:
        """
        检测悬挂任务（PENDING状态超过指定小时数）
        
        Args:
            timeout_hours: 超时时间，单位为小时，默认为1小时
            
        Returns:
            悬挂任务列表
        """
        # 计算超时时间点
        timeout_time = datetime.now(timezone.utc) - timedelta(hours=timeout_hours)
        
        return self.db.query("""
            SELECT * FROM task_instances
            WHERE status = 'PENDING'
              AND created_at < ?
            ORDER BY created_at
        """, timeout_time)
    
    def get_task_statistics(self, trace_id: str) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            任务统计信息字典
        """
        total = self.db.count_tasks(trace_id)
        completed = self.db.count_completed_tasks(trace_id)
        failed = self.db.count_tasks_by_status(trace_id, "FAILED")
        cancelled = self.db.count_tasks_by_status(trace_id, "CANCELLED")
        running = self.db.count_tasks_by_status(trace_id, "RUNNING")
        pending = self.db.count_tasks_by_status(trace_id, "PENDING")
        
        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "cancelled": cancelled,
            "running": running,
            "pending": pending,
            "progress": completed / total if total else 0.0
        }

