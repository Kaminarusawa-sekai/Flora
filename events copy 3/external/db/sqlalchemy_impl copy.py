from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_, func, text
from sqlalchemy.dialects.postgresql import array
from .base import TaskDefinitionRepository, TaskInstanceRepository
from .models import TaskInstanceDB, TaskDefinitionDB
from ...common.task_definition import TaskDefinition
from ...common.task_instance import TaskInstance
from ...common.enums import TaskInstanceStatus
import json
from datetime import datetime


class SQLAlchemyTaskInstanceRepo(TaskInstanceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_ready_tasks(self) -> list[TaskInstance]:
        # 使用单次 JOIN 查询优化，避免 N+1 查询
        # 查询思路：
        # 1. 找出所有 PENDING 状态的任务
        # 2. 对于有依赖的任务，确保所有依赖都存在且状态为 SUCCESS
        stmt = select(TaskInstanceDB).where(
            TaskInstanceDB.status == TaskInstanceStatus.PENDING
        ).outerjoin(
            TaskInstanceDB, 
            TaskInstanceDB.id == func.any(TaskInstanceDB.depends_on)
        ).group_by(
            TaskInstanceDB.id
        ).having(
            or_(
                # 无依赖
                TaskInstanceDB.depends_on == None,
                # 有依赖且所有依赖都已完成
                and_(
                    func.cardinality(TaskInstanceDB.depends_on) > 0,
                    func.count(TaskInstanceDB.id) == func.cardinality(TaskInstanceDB.depends_on),
                    func.bool_and(TaskInstanceDB.status == TaskInstanceStatus.SUCCESS)
                )
            )
        )
        
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]

    async def find_pending_with_deps_satisfied(self) -> list[TaskInstance]:
        # 该方法与 find_ready_tasks 功能相同，复用实现
        return await self.find_ready_tasks()

    async def update_fields(self, instance_id: str, **fields) -> None:
        stmt = (
            update(TaskInstanceDB)
            .where(TaskInstanceDB.id == instance_id)
            .values(**fields)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def increment_completed_children(self, parent_id: str) -> int:
        stmt = (
            update(TaskInstanceDB)
            .where(TaskInstanceDB.id == parent_id)
            .values(completed_children=TaskInstanceDB.completed_children + 1)
            .returning(TaskInstanceDB.completed_children)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    def _to_domain(self, db: TaskInstanceDB) -> TaskInstance:
        return TaskInstance(
            id=db.id,
            trace_id=db.trace_id,
            parent_id=db.parent_id,
            job_id=db.job_id,
            actor_type=db.actor_type,
            layer=db.layer,
            is_leaf_agent=db.is_leaf_agent,
            schedule_type=db.schedule_type,
            round_index=db.round_index,
            cron_trigger_time=db.cron_trigger_time,
            status=TaskInstanceStatus(db.status),
            node_path=db.node_path,
            depth=db.depth,
            depends_on=db.depends_on if db.depends_on else None,
            split_count=db.split_count,
            completed_children=db.completed_children,
            input_params=db.input_params if db.input_params else {},
            output_ref=db.output_ref,
            error_msg=db.error_msg,
            started_at=db.started_at,
            finished_at=db.finished_at,
            created_at=db.created_at,
            updated_at=db.updated_at
        )

    async def create(self, instance: TaskInstance) -> None: 
        db_instance = TaskInstanceDB(
            id=instance.id,
            trace_id=instance.trace_id,
            parent_id=instance.parent_id,
            job_id=instance.job_id,
            actor_type=instance.actor_type,
            layer=instance.layer,
            is_leaf_agent=instance.is_leaf_agent,
            schedule_type=instance.schedule_type,
            round_index=instance.round_index,
            cron_trigger_time=instance.cron_trigger_time,
            status=instance.status.value,
            node_path=instance.node_path,
            depth=instance.depth,
            depends_on=instance.depends_on,
            split_count=instance.split_count,
            completed_children=instance.completed_children,
            input_params=instance.input_params,
            output_ref=instance.output_ref,
            error_msg=instance.error_msg,
            started_at=instance.started_at,
            finished_at=instance.finished_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at
        )
        self.session.add(db_instance)
        await self.session.commit()
    
    async def get(self, instance_id: str) -> TaskInstance: 
        stmt = select(TaskInstanceDB).where(TaskInstanceDB.id == instance_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None
    
    async def get_by_ids(self, ids: list[str]) -> list[TaskInstance]: 
        stmt = select(TaskInstanceDB).where(TaskInstanceDB.id.in_(ids))
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def find_by_trace_id(self, trace_id: str) -> list[TaskInstance]: 
        stmt = select(TaskInstanceDB).where(TaskInstanceDB.trace_id == trace_id)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def find_by_trace_id_with_filters(
        self, 
        trace_id: str, 
        filters: dict, 
        limit: int = 100, 
        offset: int = 0
    ) -> list[TaskInstance]:
        """
        根据 trace_id 和多个筛选条件查询任务实例
        """
        stmt = select(TaskInstanceDB).where(TaskInstanceDB.trace_id == trace_id)
        
        for key, value in filters.items():
            column = getattr(TaskInstanceDB, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
        
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def lock_for_execution(self, instance_id: str, worker_id: str) -> bool: 
        # 使用 SELECT ... FOR UPDATE SKIP LOCKED 实现分布式锁
        stmt = (
            update(TaskInstanceDB)
            .where(
                and_(
                    TaskInstanceDB.id == instance_id,
                    TaskInstanceDB.status == TaskInstanceStatus.PENDING
                )
            )
            .values(
                status=TaskInstanceStatus.RUNNING,
                job_id=worker_id
            )
            .returning(TaskInstanceDB.id)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none() is not None
    
    async def update_status(self, instance_id: str, status: TaskInstanceStatus, **kwargs) -> None: 
        update_data = {'status': status.value}
        update_data.update(kwargs)
        
        stmt = (
            update(TaskInstanceDB)
            .where(TaskInstanceDB.id == instance_id)
            .values(**update_data)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def bulk_update_status_by_trace(self, trace_id: str, status: TaskInstanceStatus) -> None: 
        stmt = (
            update(TaskInstanceDB)
            .where(TaskInstanceDB.trace_id == trace_id)
            .values(status=status.value)
        )
        await self.session.execute(stmt)
        await self.session.commit()


class SQLAlchemyTaskDefinitionRepo(TaskDefinitionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_domain(self, db: TaskDefinitionDB) -> TaskDefinition:
        from ...common.enums import ActorType, ScheduleType
        return TaskDefinition(
            id=db.id,
            name=db.name,
            actor_type=ActorType(db.actor_type),
            role=db.role,
            code_ref=db.code_ref,
            entrypoint=db.entrypoint,
            schedule_type=ScheduleType(db.schedule_type),
            cron_expr=db.cron_expr,
            loop_config=db.loop_config,
            resource_profile=db.resource_profile,
            strategy_tags=db.strategy_tags or [],
            default_params=db.default_params or {},
            timeout_sec=db.timeout_sec,
            max_retries=db.max_retries,
            is_active=db.is_active,
            created_at=db.created_at
        )
    
    async def get(self, def_id: str) -> TaskDefinition:
        from .models import TaskDefinitionDB
        stmt = select(TaskDefinitionDB).where(TaskDefinitionDB.id == def_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None
    
    async def list_active_cron(self) -> list[TaskDefinition]:
        from .models import TaskDefinitionDB
        stmt = select(TaskDefinitionDB).where(
            TaskDefinitionDB.is_active == True,
            TaskDefinitionDB.cron_expr != None
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def get_by_job_id(self, job_id: str) -> TaskDefinition:
        from .models import TaskDefinitionDB
        stmt = select(TaskDefinitionDB).where(TaskDefinitionDB.id == job_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None
    
    async def update_last_triggered_at(self, def_id: str, timestamp: datetime) -> None:
        from .models import TaskDefinitionDB
        stmt = (
            update(TaskDefinitionDB)
            .where(TaskDefinitionDB.id == def_id)
            .values(last_triggered_at=timestamp)
        )
        await self.session.execute(stmt)
        await self.session.commit()