from typing import List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_

from ..repo import TaskDefinitionRepo, TaskInstanceRepo
from ..models import TaskDefinitionDB, TaskInstanceDB


class SQLAlchemyTaskDefinitionRepo(TaskDefinitionRepo):
    """基于SQLAlchemy的任务定义仓库实现"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, name: str, cron_expr: Optional[str] = None, loop_config: dict = None, is_active: bool = True) -> TaskDefinitionDB:
        new_def = TaskDefinitionDB(
            name=name,
            cron_expr=cron_expr,
            loop_config=loop_config or {},
            is_active=is_active
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
