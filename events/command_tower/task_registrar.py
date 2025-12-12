from typing import List
from events.command_tower.models import TaskInstance


class TaskRegistrar:
    """
    任务注册器
    负责将动态生成的任务拓扑安全写入数据库，确保结构一致性
    """
    
    def __init__(self, db_client):
        """
        初始化任务注册器
        
        Args:
            db_client: 数据库客户端，需支持 get_task、bulk_insert 等方法
        """
        self.db = db_client
    
    def register_tasks(self, tasks: List[TaskInstance]) -> List[str]:
        """
        注册任务列表
        
        Args:
            tasks: 任务实例列表
            
        Returns:
            注册成功的任务ID列表
            
        Raises:
            ValueError: 当parent_id不存在或状态不是RUNNING时
        """
        # 预计算并填充每个任务的node_path, depth, layer
        processed_tasks = []
        for task in tasks:
            # 验证parent_id存在且状态为RUNNING
            parent = self.db.get_task(task.parent_id)
            if not parent:
                raise ValueError(f"Parent task {task.parent_id} not found")
            if parent.status != "RUNNING":
                raise ValueError(f"Parent task {task.parent_id} is not in RUNNING state")
            
            # 计算layer, depth, node_path
            task.layer = parent.layer + 1 if parent.layer is not None else 1
            parent_path_depth = len(parent.node_path.strip("/").split("/")) if parent.node_path else 0
            task.depth = parent_path_depth + 1
            parent_path = parent.node_path or "/"
            task.node_path = f"{parent_path}{task.id}/"
            
            processed_tasks.append(task)
        
        # 批量原子写入
        self.db.bulk_insert(processed_tasks)
        
        return [t.id for t in processed_tasks]
    
    def validate_task_tree(self, tasks: List[TaskInstance]) -> bool:
        """
        验证任务树的完整性和一致性
        
        Args:
            tasks: 任务实例列表
            
        Returns:
            如果任务树有效返回True，否则返回False
        """
        # 检查所有parent_id都存在于列表或已存在于数据库
        task_ids = {t.id for t in tasks}
        for task in tasks:
            if task.parent_id and task.parent_id not in task_ids:
                # 检查parent_id是否已存在于数据库
                parent = self.db.get_task(task.parent_id)
                if not parent:
                    return False
        
        return True
