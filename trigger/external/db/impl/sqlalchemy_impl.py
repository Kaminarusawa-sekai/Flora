from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_

from ..repo import TaskDefinitionRepo, TaskInstanceRepo, ScheduledTaskRepo
from ..models import TaskDefinitionDB, TaskInstanceDB, ScheduledTaskDB


class SQLAlchemyTaskDefinitionRepo(TaskDefinitionRepo):
    """基于SQLAlchemy的任务定义仓库实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, name: str, content: dict = None, cron_expr: Optional[str] = None, loop_config: dict = None, schedule_type: str = "IMMEDIATE", schedule_config: dict = None, is_active: bool = True, is_temporary: bool = False, created_at: datetime = None) -> TaskDefinitionDB:
        new_def = TaskDefinitionDB(
            name=name,
            content=content or {},
            cron_expr=cron_expr,
            loop_config=loop_config or {},
            schedule_type=schedule_type,
            schedule_config=schedule_config or {},
            is_active=is_active,
            is_temporary=is_temporary,
            created_at=created_at or datetime.now(timezone.utc)
        )
        self.session.add(new_def)
        await self.session.commit()
        await self.session.refresh(new_def)
        return new_def
    
    async def get(self, def_id: str) -> Optional[TaskDefinitionDB]:
        return await self.session.get(TaskDefinitionDB, def_id)
    
    async def list_active_cron(self) -> List[TaskDefinitionDB]:
        stmt = select(TaskDefinitionDB).where(
            and_(
                TaskDefinitionDB.is_active == True,
                TaskDefinitionDB.cron_expr != None
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_last_triggered_at(self, def_id: str, last_triggered_at: datetime) -> None:
        stmt = update(TaskDefinitionDB).where(
            TaskDefinitionDB.id == def_id
        ).values(
            last_triggered_at=last_triggered_at
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def deactivate(self, def_id: str) -> None:
        stmt = update(TaskDefinitionDB).where(
            TaskDefinitionDB.id == def_id
        ).values(
            is_active=False
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def activate(self, def_id: str) -> None:
        stmt = update(TaskDefinitionDB).where(
            TaskDefinitionDB.id == def_id
        ).values(
            is_active=True
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update(self, def_id: str, **kwargs) -> Optional[TaskDefinitionDB]:
        """更新任务定义"""
        # 只允许更新特定字段
        allowed_fields = {'cron_expr', 'loop_config', 'schedule_config', 'is_active', 'content', 'name', 'schedule_type'}
        update_values = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

        if not update_values:
            return await self.get(def_id)

        update_values['updated_at'] = datetime.now(timezone.utc)

        stmt = update(TaskDefinitionDB).where(
            TaskDefinitionDB.id == def_id
        ).values(**update_values)

        await self.session.execute(stmt)
        await self.session.commit()

        return await self.get(def_id)


class SQLAlchemyTaskInstanceRepo(TaskInstanceRepo):
    """基于SQLAlchemy的任务实例仓库实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, definition_id: str, trace_id: str, input_params: dict = None, schedule_type: str = "ONCE", round_index: int = 0, depends_on: list = None) -> TaskInstanceDB:
        new_instance = TaskInstanceDB(
            definition_id=definition_id,
            trace_id=trace_id,
            input_params=input_params or {},
            schedule_type=schedule_type,
            round_index=round_index,
            depends_on=depends_on or []
        )
        self.session.add(new_instance)
        await self.session.commit()
        await self.session.refresh(new_instance)
        return new_instance
    
    async def get(self, instance_id: str) -> Optional[TaskInstanceDB]:
        return await self.session.get(TaskInstanceDB, instance_id)
    
    async def update_status(self, instance_id: str, status: str, error_msg: Optional[str] = None) -> None:
        updates = {"status": status}
        if error_msg:
            updates["error_msg"] = error_msg
        if status == "RUNNING":
            updates["started_at"] = datetime.now(timezone.utc)
        stmt = update(TaskInstanceDB).where(
            TaskInstanceDB.id == instance_id
        ).values(**updates)
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def list_by_trace_id(self, trace_id: str) -> List[TaskInstanceDB]:
        stmt = select(TaskInstanceDB).where(
            TaskInstanceDB.trace_id == trace_id
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_finished_at(self, instance_id: str, finished_at: datetime, status: str, output_ref: Optional[str] = None, error_msg: Optional[str] = None) -> None:
        updates = {
            "finished_at": finished_at,
            "status": status
        }
        if output_ref:
            updates["output_ref"] = output_ref
        if error_msg:
            updates["error_msg"] = error_msg
        stmt = update(TaskInstanceDB).where(
            TaskInstanceDB.id == instance_id
        ).values(**updates)
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def get_running_instances(self, timeout_seconds: int = 3600) -> List[TaskInstanceDB]:
        """获取运行超时的任务实例"""
        timeout_threshold = datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)
        stmt = select(TaskInstanceDB).where(
            and_(
                TaskInstanceDB.status == "RUNNING",
                TaskInstanceDB.started_at < timeout_threshold
            )
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()





class SQLAlchemyScheduledTaskRepo(ScheduledTaskRepo):
    """基于SQLAlchemy的调度任务仓库实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, task) -> any:
        """创建调度任务"""
        db_task = ScheduledTaskDB(
            id=task.id,
            definition_id=task.definition_id,
            trace_id=task.trace_id,
            status=task.status,
            schedule_type=task.schedule_type,
            scheduled_time=task.scheduled_time,
            execute_after=task.execute_after,
            schedule_config=task.schedule_config,
            round_index=task.round_index,
            input_params=task.input_params,
            priority=task.priority,
            max_retries=task.max_retries,
            retry_count=task.retry_count,
            created_at=task.created_at,
            depends_on=task.depends_on
        )
        
        self.session.add(db_task)
        await self.session.flush()
        await self.session.commit()
        await self.session.refresh(db_task)
        return db_task
    
    async def get(self, task_id: str) -> Optional[ScheduledTaskDB]:
        """获取单个调度任务"""
        return await self.session.get(ScheduledTaskDB, task_id)
    
    async def get_pending_tasks(self, before_time: datetime, limit: int = 100) -> List[ScheduledTaskDB]:
        """获取待处理的调度任务"""
        stmt = (
            select(ScheduledTaskDB)
            .where(
                and_(
                    ScheduledTaskDB.status == "PENDING",
                    ScheduledTaskDB.scheduled_time <= before_time,
                    or_(
                        ScheduledTaskDB.execute_after.is_(None),
                        ScheduledTaskDB.execute_after <= before_time
                    ),
                    ScheduledTaskDB.cancelled_at.is_(None)
                )
            )
            .order_by(
                ScheduledTaskDB.priority.desc(),
                ScheduledTaskDB.scheduled_time.asc()
            )
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        return result.scalars().all()
    
    async def update_status(self, task_id: str, status: str) -> bool:
        """更新调度任务状态"""
        stmt = (
            update(ScheduledTaskDB)
            .where(ScheduledTaskDB.id == task_id)
            .values(
                status=status
            )
        )
        
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
    
    async def record_retry(self, task_id: str, error_msg: str) -> None:
        """记录任务重试"""
        # 先获取当前任务
        task = await self.session.get(ScheduledTaskDB, task_id)
        if task:
            task.retry_count += 1
            task.error_msg = error_msg
            await self.session.commit()
            await self.session.refresh(task)
    
    async def update_scheduled_task(self, task_id: str, **kwargs) -> Optional[ScheduledTaskDB]:
        """
        更新调度任务

        只允许修改 PENDING 状态的任务
        """
        # 先检查任务状态
        task = await self.session.get(ScheduledTaskDB, task_id)
        if not task:
            return None

        if task.status != "PENDING":
            raise ValueError(f"Cannot update task in {task.status} status, only PENDING tasks can be updated")

        # 只允许更新特定字段
        allowed_fields = {'scheduled_time', 'schedule_config', 'input_params', 'priority', 'execute_after'}
        update_values = {k: v for k, v in kwargs.items() if k in allowed_fields and v is not None}

        if not update_values:
            return task

        stmt = update(ScheduledTaskDB).where(
            ScheduledTaskDB.id == task_id
        ).values(**update_values)

        await self.session.execute(stmt)
        await self.session.commit()

        return await self.get(task_id)

    async def reschedule_task(self, task_id: str, new_scheduled_time: datetime, new_schedule_config: dict = None) -> Optional[ScheduledTaskDB]:
        """
        重新调度任务

        将任务状态重置为 PENDING，并更新调度时间
        只允许对 FAILED、CANCELLED 状态的任务进行重新调度
        """
        task = await self.session.get(ScheduledTaskDB, task_id)
        if not task:
            return None

        # 只允许重新调度已完成或已取消的任务
        if task.status not in ("FAILED", "CANCELLED", "SUCCESS"):
            raise ValueError(f"Cannot reschedule task in {task.status} status")

        update_values = {
            "status": "PENDING",
            "scheduled_time": new_scheduled_time,
            "retry_count": 0,
            "error_msg": None,
            "cancelled_at": None,
            "started_at": None,
            "finished_at": None
        }

        if new_schedule_config is not None:
            update_values["schedule_config"] = new_schedule_config

        stmt = update(ScheduledTaskDB).where(
            ScheduledTaskDB.id == task_id
        ).values(**update_values)

        await self.session.execute(stmt)
        await self.session.commit()

        return await self.get(task_id)

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消调度任务

        只允许取消 PENDING 或 SCHEDULED 状态的任务
        """
        task = await self.session.get(ScheduledTaskDB, task_id)
        if not task:
            return False

        if task.status not in ("PENDING", "SCHEDULED"):
            return False

        stmt = update(ScheduledTaskDB).where(
            ScheduledTaskDB.id == task_id
        ).values(
            status="CANCELLED",
            cancelled_at=datetime.now(timezone.utc)
        )

        result = await self.session.execute(stmt)
        await self.session.commit()

        return result.rowcount > 0