from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any

from external.db.base import TaskInstanceRepository
from external.db.models import TaskInstanceDB
from ...common.task_instance import TaskInstance
from ...common.enums import TaskInstanceStatus


class SQLiteTaskInstanceRepository(TaskInstanceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_ready_tasks(self) -> List[TaskInstance]:
        # SQLite 不支持复杂的 array 函数和 JOIN 查询，使用 N+1 查询方式
        # 先查所有 PENDING 状态的任务
        stmt = select(TaskInstanceDB).where(TaskInstanceDB.status == TaskInstanceStatus.PENDING)
        result = await self.session.execute(stmt)
        pending_tasks = result.scalars().all()
        ready = []

        for task_db in pending_tasks:
            deps = task_db.depends_on or []
            if not deps:
                # 无依赖，直接就绪
                ready.append(self._to_domain(task_db))
            else:
                # 查依赖任务状态
                dep_ids = [d for d in deps]  # 假设 depends_on 是 list[str]
                dep_stmt = select(TaskInstanceDB).where(TaskInstanceDB.id.in_(dep_ids))
                dep_result = await self.session.execute(dep_stmt)
                dep_map = {d.id: d.status for d in dep_result.scalars()}
                
                # 检查所有依赖是否都已成功
                all_deps_success = True
                for dep_id in deps:
                    if dep_map.get(dep_id) != TaskInstanceStatus.SUCCESS:
                        all_deps_success = False
                        break
                
                if all_deps_success:
                    ready.append(self._to_domain(task_db))
        return ready

    async def find_pending_with_deps_satisfied(self) -> List[TaskInstance]:
        # 该方法与 find_ready_tasks 功能相同，复用实现
        return await self.find_ready_tasks()

    async def update_fields(self, instance_id: str, fields: Dict[str, Any]) -> None:
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
    
    async def get(self, instance_id: str) -> Optional[TaskInstance]: 
        stmt = select(TaskInstanceDB).where(TaskInstanceDB.id == instance_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None
    
    async def get_by_ids(self, ids: List[str]) -> List[TaskInstance]: 
        stmt = select(TaskInstanceDB).where(TaskInstanceDB.id.in_(ids))
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def find_by_trace_id(self, trace_id: str) -> List[TaskInstance]: 
        stmt = select(TaskInstanceDB).where(TaskInstanceDB.trace_id == trace_id)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def find_by_trace_id_with_filters(self, trace_id: str, filters: dict, limit: int = 100, offset: int = 0) -> List[TaskInstance]:
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
        # SQLite 不支持 SELECT ... FOR UPDATE SKIP LOCKED，直接更新状态
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
