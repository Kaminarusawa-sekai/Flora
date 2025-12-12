from datetime import datetime, timedelta
from typing import Optional
from events.command_tower.models import TaskDefinition, TaskInstance
from events.common.actor_dto import ActorType


class LifecycleManager:
    """
    生命周期管理器
    管理任务的启动、清理、循环调度（Cron）
    """
    
    def __init__(self, db_client, task_registrar):
        """
        初始化生命周期管理器
        
        Args:
            db_client: 数据库客户端，需支持相关操作方法
            task_registrar: 任务注册器实例，用于注册新任务
        """
        self.db = db_client
        self.task_registrar = task_registrar
    
    def start_root_task(self, definition_id: str, 
                       input_params: Optional[dict] = None,
                       trace_id: Optional[str] = None) -> str:
        """
        启动根任务
        
        Args:
            definition_id: 任务定义ID
            input_params: 输入参数，默认为None
            trace_id: 可选，指定跟踪ID，默认为None（自动生成）
            
        Returns:
            启动的根任务ID
        """
        # 获取任务定义
        definition = self.db.get_task_definition(definition_id)
        if not definition:
            raise ValueError(f"Task definition {definition_id} not found")
        
        # 创建根任务实例
        root_task = TaskInstance(
            id=self.db.generate_task_id(),
            definition_id=definition_id,
            trace_id=trace_id or self.db.generate_trace_id(),
            parent_id=None,
            actor_type=ActorType.AGENT,
            actor_id="root_agent",
            name=definition.name,
            status="RUNNING",
            layer=0,
            depth=0,
            node_path="/",
            input_params=input_params or {},
            priority=definition.priority,
            resource_profile=definition.resource_profile,
            strategy_tags=definition.strategy_tags,
            max_retries=definition.max_retries,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )
        
        # 写入数据库
        self.db.insert_task(root_task)
        
        return root_task.id
    
    def cleanup_old_tasks(self, days: int = 30):
        """
        清理过期任务
        
        Args:
            days: 过期天数，默认为30天
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # 归档或删除旧任务
        self.db.archive_old_tasks(cutoff_date)
    
    def retry_failed_tasks(self):
        """
        重试失败的叶子执行任务
        """
        # 查询需要重试的任务
        failed_tasks = self.db.query("""
            SELECT * FROM task_instances
            WHERE status = 'FAILED'
              AND actor_type = 'EXECUTION'
              AND retry_count < max_retries
        """)
        
        for task in failed_tasks:
            # 重新设置为PENDING状态，增加重试计数
            task.status = "PENDING"
            task.retry_count += 1
            task.updated_at = datetime.utcnow()
            
            self.db.update_task(task)
    
    def handle_loop_completion(self, trace_id: str):
        """
        处理循环任务完成
        
        Args:
            trace_id: 跟踪ID
        """
        # 获取循环任务定义
        root_task = self.db.get_root_task(trace_id)
        if not root_task:
            return
        
        definition = self.db.get_task_definition(root_task.definition_id)
        if not definition or definition.schedule_type != "LOOP":
            return
        
        # 获取当前轮次
        current_round = self.db.get_current_loop_round(trace_id)
        
        # 检查是否需要继续循环
        loop_config = definition.loop_config or {}
        max_rounds = loop_config.get("max_rounds", 5)
        
        if current_round < max_rounds:
            # 触发新一轮循环
            self._trigger_next_loop_round(trace_id, definition, current_round + 1)
        else:
            # 循环结束，标记任务完成
            self.db.mark_task_tree_completed(trace_id)
    
    def _trigger_next_loop_round(self, trace_id: str, 
                                definition: TaskDefinition, 
                                round_index: int):
        """
        触发新一轮循环
        
        Args:
            trace_id: 跟踪ID
            definition: 任务定义
            round_index: 新轮次索引
        """
        # 创建新一轮的根任务（复用相同trace_id）
        next_round_root = TaskInstance(
            id=self.db.generate_task_id(),
            definition_id=definition.id,
            trace_id=trace_id,
            parent_id=None,
            actor_type=ActorType.AGENT,
            actor_id="loop_agent",
            name=f"{definition.name} - Round {round_index}",
            status="RUNNING",
            layer=0,
            depth=0,
            node_path=f"/round_{round_index}/",
            input_params={"round_index": round_index},
            priority=definition.priority,
            resource_profile=definition.resource_profile,
            strategy_tags=definition.strategy_tags,
            max_retries=definition.max_retries,
            created_at=datetime.utcnow(),
            started_at=datetime.utcnow()
        )
        
        # 写入数据库
        self.db.insert_task(next_round_root)
