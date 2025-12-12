from typing import List, Dict, Any
from events.command_tower.models import TaskInstance

class DAGDispatcherCoordinator:
    """DAG调度协调器，提供调度元信息，支持按依赖顺序和资源标签查询可执行任务"""
    
    def __init__(self, db_client):
        """初始化DAG调度协调器
        
        Args:
            db_client: 数据库客户端，需支持相关查询方法
        """
        self.db = db_client
    
    def get_executable_tasks(self, trace_id: str) -> List[TaskInstance]:
        """获取可执行任务列表
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            可执行的任务实例列表
        """
        return self.db.query_executable_tasks(trace_id)
    
    def get_assignable_tasks(self, dispatcher_tags: List[str], 
                           dispatcher_resource: str = "default") -> List[TaskInstance]:
        """获取可分配给特定Dispatcher的任务列表
        
        Args:
            dispatcher_tags: Dispatcher的策略标签列表
            dispatcher_resource: Dispatcher的资源配置，默认为"default"
            
        Returns:
            可分配的任务实例列表
        """
        return self.db.query("""
            SELECT * FROM task_instances 
            WHERE status = 'PENDING' 
              AND (depends_on IS NULL OR all_deps_done) 
              AND (resource_profile IN ('default', ?) OR ? = 'default') 
              AND strategy_tags && ?  -- PostgreSQL array intersection
            ORDER BY priority DESC, created_at
        """, dispatcher_resource, dispatcher_resource, dispatcher_tags)
    
    def get_task_batches_by_dependency(self, trace_id: str) -> List[List[TaskInstance]]:
        """获取按依赖顺序分组的任务批次
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            任务批次列表，每个批次内的任务无依赖关系，批次间按依赖顺序执行
        """
        # 获取所有待执行任务
        executable_tasks = self.get_executable_tasks(trace_id)
        
        # 按优先级和创建时间排序
        sorted_tasks = sorted(executable_tasks, key=lambda x: (-x.priority, x.created_at))
        
        # 简单批次划分：同一优先级的任务为一批
        batches = []
        current_priority = None
        current_batch = []
        
        for task in sorted_tasks:
            if task.priority != current_priority:
                if current_batch:
                    batches.append(current_batch)
                    current_batch = []
                current_priority = task.priority
            current_batch.append(task)
        
        if current_batch:
            batches.append(current_batch)
        
        return batches
    
    def get_tasks_with_priority(self, trace_id: str, 
                              min_priority: int = 0) -> List[TaskInstance]:
        """获取指定优先级以上的任务
        
        Args:
            trace_id: 跟踪ID
            min_priority: 最小优先级
            
        Returns:
            符合优先级要求的任务实例列表
        """
        return self.db.query_tasks_by_priority(trace_id, min_priority)
