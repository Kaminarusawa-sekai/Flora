import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any
from croniter import croniter

from common.models import ScheduleType, TaskStatus, ScheduledTask
from external.db.impl import create_scheduled_task_repo, create_task_definition_repo
from external.db.session import dialect
from external.messaging.base import MessageBroker


class SchedulerService:
    """调度服务 - 使用现有模型结构"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
    
    async def create_scheduled_task(
        self,
        session: AsyncSession,
        definition_id: str,
        trace_id: str,
        scheduled_time: datetime,
        schedule_type: ScheduleType,
        schedule_config: Dict[str, Any],
        input_params: Dict[str, Any],
        round_index: int = 0,
        priority: int = 0
    ) -> str:
        """创建调度任务记录"""
        repo = create_scheduled_task_repo(session, dialect)
        
        # 创建调度任务对象
        scheduled_task = ScheduledTask(
            id=str(uuid.uuid4()),
            definition_id=definition_id,
            trace_id=trace_id,
            status=TaskStatus.PENDING,
            schedule_type=schedule_type,
            scheduled_time=scheduled_time,
            schedule_config=schedule_config,
            input_params=input_params,
            round_index=round_index,
            priority=priority,
            created_at=datetime.now(timezone.utc)
        )
        
        # 保存到数据库，只负责写
        db_task = await repo.create(scheduled_task)
        return db_task.id
    
    async def schedule_immediate(
        self,
        session: AsyncSession,
        definition_id: str,
        input_params: Dict[str, Any],
        trace_id: Optional[str] = None,
        priority: int = 0
    ) -> str:
        """调度立即执行任务"""
        return await self.create_scheduled_task(
            session=session,
            definition_id=definition_id,
            trace_id=trace_id or str(uuid.uuid4()),
            scheduled_time=datetime.now(timezone.utc),
            schedule_type=ScheduleType.IMMEDIATE,
            schedule_config={"type": "immediate"},
            input_params=input_params,
            priority=priority
        )
    
    async def schedule_delayed(
        self,
        session: AsyncSession,
        definition_id: str,
        input_params: Dict[str, Any],
        delay_seconds: int,
        trace_id: Optional[str] = None,
        priority: int = 0
    ) -> str:
        """调度延迟任务"""
        scheduled_time = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        return await self.create_scheduled_task(
            session=session,
            definition_id=definition_id,
            trace_id=trace_id or str(uuid.uuid4()),
            scheduled_time=scheduled_time,
            schedule_type=ScheduleType.DELAYED,
            schedule_config={
                "type": "delayed",
                "delay_seconds": delay_seconds,
                "original_scheduled": scheduled_time.isoformat()
            },
            input_params=input_params,
            priority=priority
        )
    
    async def schedule_cron(
        self,
        session: AsyncSession,
        definition_id: str,
        cron_expression: str,
        input_params: Dict[str, Any],
        start_from: Optional[datetime] = None,
        trace_id: Optional[str] = None
    ) -> str:
        """调度CRON定时任务"""
        now = datetime.now(timezone.utc)
        base_time = start_from or now
        
        # 计算下一次执行时间
        cron = croniter(cron_expression, base_time)
        next_run = cron.get_next(datetime)
        
        return await self.create_scheduled_task(
            session=session,
            definition_id=definition_id,
            trace_id=trace_id or str(uuid.uuid4()),
            scheduled_time=next_run,
            schedule_type=ScheduleType.CRON,
            schedule_config={
                "type": "cron",
                "expression": cron_expression,
                "original_scheduled": next_run.isoformat()
            },
            input_params=input_params
        )
    
    async def schedule_loop(
        self,
        session: AsyncSession,
        definition_id: str,
        input_params: Dict[str, Any],
        max_rounds: int,
        loop_interval: Optional[int] = None,
        trace_id: Optional[str] = None
    ) -> str:
        """调度循环任务"""
        trace_id = trace_id or str(uuid.uuid4())
        schedule_type = ScheduleType.LOOP if not loop_interval else ScheduleType.INTERVAL_LOOP
        
        # 创建第一轮任务
        first_task_id = await self.create_scheduled_task(
            session=session,
            definition_id=definition_id,
            trace_id=trace_id,
            scheduled_time=datetime.now(timezone.utc),
            schedule_type=schedule_type,
            schedule_config={
                "type": "loop" if not loop_interval else "interval_loop",
                "max_rounds": max_rounds,
                "loop_interval": loop_interval,
                "original_scheduled": datetime.now(timezone.utc).isoformat()
            },
            input_params=input_params,
            round_index=0
        )
        
        return first_task_id
    
    async def trigger_loop_once(
        self,
        session: AsyncSession,
        definition_id: str,
        input_params: Dict[str, Any],
        trace_id: Optional[str] = None
    ) -> str:
        """触发循环任务的一次执行"""
        return await self.create_scheduled_task(
            session=session,
            definition_id=definition_id,
            trace_id=trace_id or str(uuid.uuid4()),
            scheduled_time=datetime.now(timezone.utc),
            schedule_type=ScheduleType.LOOP,
            schedule_config={"type": "loop_once"},
            input_params=input_params
        )
