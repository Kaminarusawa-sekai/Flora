import uuid
import logging
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from datetime import datetime
from typing import Optional, Dict, Any

from thespian.actors import ActorSystem

from .task_models import TaskTriggerType, TaskStatus, TaskDefinition, TaskInstance
from .task_repository import TaskRepository

class TaskControlService:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TaskControlService, cls).__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self.logger = logging.getLogger("TaskControlService")
        self.logger.setLevel(logging.INFO)
        
        # 初始化Actor系统
        self.actor_system = ActorSystem()
        
        # 初始化任务仓库
        self.repo = TaskRepository()
        
        # 内存映射：记录正在运行的任务实例
        self._runtime_map = {}  # instance_id -> ActorAddress
        
        # 初始化调度器 (使用数据库存储，重启后任务不丢失)
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///jobs.sqlite')
        }
        
        self.scheduler = BackgroundScheduler(jobstores=jobstores)
        self.scheduler.start()
        self.logger.info("TaskControlService initialized with APScheduler")

    def create_task(self, user_id: str, content: str,
                 trigger_type: TaskTriggerType = TaskTriggerType.IMMEDIATE,
                 trigger_args: Dict[str, Any] = None) -> str:
        """
        创建一个任务（可能是立即的，也可能是定时的）
        返回 task_def_id
        """
        task_def_id = str(uuid.uuid4())
        trigger_args = trigger_args or {}

        # 1. 保存任务定义到 DB
        self.repo.create_definition(task_def_id, user_id, content, trigger_type, trigger_args)

        # 2. 根据类型调度
        if trigger_type == TaskTriggerType.IMMEDIATE:
            # 立即执行：直接触发一次实例
            self._spawn_instance(task_def_id, content)
            
        elif trigger_type == TaskTriggerType.SCHEDULED:
            # 定时任务：添加到调度器
            run_date = trigger_args.get('run_date')  # datetime对象
            if not run_date:
                raise ValueError("run_date is required for SCHEDULED trigger type")
            
            self.scheduler.add_job(
                func=self._spawn_instance,
                trigger=DateTrigger(run_date=run_date),
                args=[task_def_id, content],
                id=task_def_id,
                replace_existing=True
            )
            self.logger.info(f"Added scheduled task {task_def_id} to run at {run_date}")
            
        elif trigger_type == TaskTriggerType.LOOP:
            # 循环任务：添加到调度器
            interval_seconds = trigger_args.get('interval')
            cron_expr = trigger_args.get('cron')
            
            if interval_seconds:
                # 间隔循环
                self.scheduler.add_job(
                    func=self._spawn_instance,
                    trigger=IntervalTrigger(seconds=interval_seconds),
                    args=[task_def_id, content],
                    id=task_def_id,
                    replace_existing=True
                )
                self.logger.info(f"Added loop task {task_def_id} with interval {interval_seconds}s")
            elif cron_expr:
                # Cron表达式循环
                self.scheduler.add_job(
                    func=self._spawn_instance,
                    trigger=CronTrigger.from_crontab(cron_expr),
                    args=[task_def_id, content],
                    id=task_def_id,
                    replace_existing=True
                )
                self.logger.info(f"Added cron task {task_def_id} with expr {cron_expr}")
            else:
                raise ValueError("Either interval or cron is required for LOOP trigger type")
            
        self.logger.info(f"Task {task_def_id} created as {trigger_type}")
        return task_def_id

    def _spawn_instance(self, task_def_id: str, content: str):
        """
        调度器回调函数。
        每次时间到了，就调用这个方法，生成一个真正的 Actor 去执行。
        """
        # 生成本次运行的实例ID
        instance_id = f"{task_def_id}_{int(datetime.now().timestamp())}"
        
        self.logger.info(f"Spawning instance {instance_id} for definition {task_def_id}")
        
        # 创建 Actor
        try:
            from tasks.agents.agent_actor import AgentActor
            from common.messages.agent_messages import AgentTaskMessage
            
            agent = self.actor_system.createActor(AgentActor)
            
            # 记录运行状态
            self._runtime_map[instance_id] = agent
            self.repo.record_instance_start(instance_id, task_def_id, content)
            
            # 发送开始指令
            task_message = AgentTaskMessage(
                task_id=instance_id,
                content=content,
                user_id="system",  # 系统触发
                agent_id="system_agent",
                reply_to=None
            )
            
            self.actor_system.tell(agent, task_message)
        except Exception as e:
            self.logger.error(f"Failed to spawn instance {instance_id}: {str(e)}", exc_info=True)
            # 记录失败状态
            self.repo.record_instance_complete(
                instance_id=instance_id,
                error=str(e)
            )

    def pause_schedule(self, task_def_id: str):
        """暂停循环任务的调度（不生成新实例，但不影响正在跑的）"""
        if self.scheduler.get_job(task_def_id):
            self.scheduler.pause_job(task_def_id)
            self.repo.update_def_status(task_def_id, TaskStatus.PAUSED)
            self.logger.info(f"Schedule {task_def_id} paused.")
        else:
            self.logger.warning(f"Job {task_def_id} not found in scheduler")

    def resume_schedule(self, task_def_id: str):
        """恢复循环任务的调度"""
        if self.scheduler.get_job(task_def_id):
            self.scheduler.resume_job(task_def_id)
            self.repo.update_def_status(task_def_id, TaskStatus.ACTIVE)
            self.logger.info(f"Schedule {task_def_id} resumed.")
        else:
            self.logger.warning(f"Job {task_def_id} not found in scheduler")

    def cancel_task(self, task_def_id: str):
        """
        彻底取消任务：
        1. 移除调度规则 (不再生成新的)
        2. 杀死当前正在运行的实例 (如果有)
        """
        # 1. 移除调度
        if self.scheduler.get_job(task_def_id):
            self.scheduler.remove_job(task_def_id)
            self.logger.info(f"Removed scheduler job {task_def_id}")
        
        # 2. 更新 DB 状态
        self.repo.update_def_status(task_def_id, TaskStatus.CANCELLED)
        
        # 3. 查找所有属于该定义的正在运行的实例，并终止它们
        active_instances = [(inst_id, addr) for inst_id, addr in self._runtime_map.items()
                          if inst_id.startswith(task_def_id)]
        
        for inst_id, addr in active_instances:
            self.logger.info(f"Killing active instance {inst_id}")
            self.actor_system.tell(addr, {'type': 'CANCEL_TASK'})
            del self._runtime_map[inst_id]
            # 记录取消状态
            self.repo.record_instance_complete(
                instance_id=inst_id,
                error="Task cancelled by user"
            )

    def trigger_immediately(self, task_def_id: str):
        """手动触发一次循环任务（立即执行，不影响原有时刻表）"""
        task_def = self.repo.get_definition(task_def_id)
        if task_def:
            self._spawn_instance(task_def_id, task_def.content)
            self.logger.info(f"Manually triggered task {task_def_id}")
        else:
            self.logger.warning(f"Task definition {task_def_id} not found")
    
    def get_task_definition(self, task_def_id: str) -> Optional[TaskDefinition]:
        """获取任务定义"""
        return self.repo.get_definition(task_def_id)
    
    def get_task_instances(self, task_def_id: str) -> list[TaskInstance]:
        """获取任务的所有实例"""
        return self.repo.get_instances_by_definition(task_def_id)
    
    def get_user_tasks(self, user_id: str) -> list[TaskDefinition]:
        """获取用户的所有任务定义"""
        return self.repo.get_definitions_by_user(user_id)
    
    def shutdown(self):
        """关闭任务控制服务"""
        self.scheduler.shutdown()
        self.logger.info("TaskControlService shutdown")

# 创建任务控制服务单例实例
task_control_service = TaskControlService()