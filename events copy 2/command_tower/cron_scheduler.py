from datetime import datetime
from typing import List

# 尝试导入croniter模块，若缺失则提供优雅的错误处理
try:
    from croniter import croniter
    HAS_CRONITER = True
except ImportError:
    HAS_CRONITER = False
    croniter = None

from events.command_tower.models import TaskDefinition, ScheduledRun
from events.command_tower.lifecycle_manager import LifecycleManager


class CronScheduler:
    """
    定时任务管理器
    扫描CRON类型的任务定义，在指定时间点触发任务执行
    """
    
    def __init__(self, db_client, lifecycle_manager):
        """
        初始化定时任务管理器
        
        Args:
            db_client: 数据库客户端，需支持相关查询和操作方法
            lifecycle_manager: 生命周期管理器实例，用于启动根任务
        """
        self.db = db_client
        self.lifecycle_manager = lifecycle_manager
    
    def run(self):
        """
        执行一次定时任务检查
        扫描所有CRON类型的任务定义，判断是否需要触发
        """
        # 检查是否有croniter模块
        if not HAS_CRONITER:
            return  # 若缺少croniter模块，则跳过执行
        
        # 获取所有CRON类型的任务定义
        cron_definitions = self.db.query("""
            SELECT * FROM task_definitions
            WHERE schedule_type = 'CRON'
              AND cron_expr IS NOT NULL
        """)
        
        for definition in cron_definitions:
            self._check_and_trigger_cron_task(definition)
    
    def _check_and_trigger_cron_task(self, definition: TaskDefinition):
        """
        检查并触发CRON任务
        
        Args:
            definition: CRON类型的任务定义
        """
        # 获取该任务定义的最后一次运行记录
        last_run = self.db.get_last_scheduled_run(definition.id)
        
        # 计算下一次运行时间
        if last_run:
            # 从上一次运行时间开始计算
            cron = croniter(definition.cron_expr, last_run.triggered_at)
        else:
            # 从当前时间开始计算
            cron = croniter(definition.cron_expr, datetime.utcnow())
        
        next_run_time = cron.get_next(datetime)
        
        # 检查是否需要触发
        if next_run_time <= datetime.utcnow():
            # 触发任务执行
            trace_id = self.lifecycle_manager.start_root_task(
                definition_id=definition.id
            )
            
            # 记录运行记录
            scheduled_run = ScheduledRun(
                id=self.db.generate_id(),
                definition_id=definition.id,
                trace_id=trace_id,
                scheduled_at=next_run_time,
                triggered_at=datetime.utcnow(),
                status="SUCCESS"
            )
            
            self.db.insert_scheduled_run(scheduled_run)
    
    def get_scheduled_runs(self, definition_id: str, 
                          start_time: datetime = None, 
                          end_time: datetime = None) -> List[ScheduledRun]:
        """
        获取指定任务定义的定时运行记录
        
        Args:
            definition_id: 任务定义ID
            start_time: 开始时间，可选
            end_time: 结束时间，可选
            
        Returns:
            定时运行记录列表
        """
        return self.db.query_scheduled_runs(
            definition_id=definition_id,
            start_time=start_time,
            end_time=end_time
        )
