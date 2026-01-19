import asyncio
import logging
from typing import Dict, Any
from datetime import datetime, timezone

from external.messaging.base import MessageBroker
from external.db.session import async_session_factory, dialect
from external.db.impl import create_scheduled_task_repo
from services.lifecycle_service import LifecycleService
from events.event_publisher import push_status_to_external

logger = logging.getLogger(__name__)


class ScheduleDispatcher:
    """
    调度分发器 - 消费调度消息并推送到外部系统
    替代原来的TaskDispatcher，更专注于调度表逻辑
    """
    
    def __init__(
        self,
        broker: MessageBroker,
        lifecycle_service: LifecycleService
    ):
        self.broker = broker
        self.lifecycle_service = lifecycle_service
    
    async def start(self):
        """
        启动调度分发器，消费两类消息：
        1. task.scheduled - 待执行任务
        2. task.status_update - 状态更新（来自外部系统）
        """
        await asyncio.gather(
            self.broker.consume("task.scheduled", self._handle_scheduled_task),
            self.broker.consume("task.status_update", self._handle_status_update)
        )
    
    async def _handle_scheduled_task(self, msg: Dict[str, Any]):
        """
        处理调度任务 - 推送到外部系统
        """
        task_id = msg["task_id"]
        
        try:
            # 验证任务是否还存在且未被取消
            async with async_session_factory() as session:
                repo = create_scheduled_task_repo(session, dialect)
                task = await repo.get(task_id)
                
                if not task or task.status != "SCHEDULED":
                    logger.warning(f"Task {task_id} not found or already processed")
                    return
                
                # 推送到外部系统
                success = await push_status_to_external(
                    task_id=task_id,
                    trace_id=task.trace_id,
                    status="READY_FOR_EXECUTION",
                    scheduled_time=task.scheduled_time,
                    metadata={
                        "definition_id": task.definition_id,
                        "trace_id": task.trace_id,
                        "input_params": task.input_params,
                        "schedule_config": task.schedule_config,
                        "round_index": task.round_index
                    }
                )
                
                if success:
                    # 更新任务状态为已分发
                    await repo.update_status(task_id, "DISPATCHED")
                    logger.info(f"Dispatched task {task_id} to external system")
                else:
                    # 分发失败，标记为失败或重试
                    await repo.record_retry(task_id, "Failed to dispatch to external system")
                    logger.error(f"Failed to dispatch task {task_id}")
                    
        except Exception as e:
            logger.error(f"Error handling scheduled task {task_id}: {e}", exc_info=True)
    
    async def _handle_status_update(self, msg: Dict[str, Any]):
        """
        处理来自外部系统的状态更新
        """
        task_id = msg["task_id"]
        status = msg["status"]
        timestamp = msg.get("timestamp")
        
        logger.info(f"External system updated task {task_id} to {status} at {timestamp}")
        
        # 如果需要，可以在这里触发一些清理或后续动作
        if status in ["SUCCESS", "FAILED", "CANCELLED"]:
            # 对于已完成的任务，我们可以清理或归档
            await self._handle_task_completion(task_id, status, msg.get("metadata"))
    
    async def _handle_task_completion(self, task_id: str, status: str, metadata: dict):
        """
        处理任务完成后的逻辑
        """
        async with async_session_factory() as session:
            repo = create_scheduled_task_repo(session, dialect)
            task = await repo.get(task_id)
            
            if not task:
                return
            
            # 根据调度配置决定是否需要创建下一次执行
            schedule_config = task.schedule_config
            schedule_type = schedule_config.get("type")
            
            if schedule_type == "cron":
                # 对于CRON任务，创建下一次执行
                await self._reschedule_cron_task(session, task, schedule_config)
            elif schedule_type in ["loop", "interval_loop"]:
                # 对于循环任务，检查是否需要下一轮
                await self._reschedule_loop_task(session, task, schedule_config)
            
            # 标记任务为完成
            await repo.update_status(task_id, status.upper())
    
    async def _reschedule_cron_task(self, session, task, schedule_config):
        """为CRON任务重新安排下一次执行"""
        cron_expr = schedule_config.get("expression")
        
        if cron_expr:
            from ...services.scheduler_service import SchedulerService
            
            scheduler = SchedulerService(self.broker)
            await scheduler.schedule_cron(
                session=session,
                definition_id=task.definition_id,
                cron_expression=cron_expr,
                input_params=task.input_params,
                trace_id=task.trace_id
            )
    
    async def _reschedule_loop_task(self, session, task, schedule_config):
        """为循环任务安排下一轮执行"""
        loop_interval = schedule_config.get("loop_interval")
        max_rounds = schedule_config.get("max_rounds", 1)
        
        if loop_interval and task.round_index + 1 < max_rounds:
            from ...services.scheduler_service import SchedulerService
            
            scheduler = SchedulerService(self.broker)
            await scheduler.create_scheduled_task(
                session=session,
                definition_id=task.definition_id,
                trace_id=task.trace_id,
                scheduled_time=datetime.now(timezone.utc) + datetime.timedelta(seconds=loop_interval),
                schedule_type=task.schedule_type,
                schedule_config=schedule_config,
                input_params=task.input_params,
                round_index=task.round_index + 1
            )
