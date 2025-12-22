from sqlalchemy import select, update, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import array
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..base import EventInstanceRepository, EventDefinitionRepository, EventLogRepository
from ..models import EventInstanceDB, EventDefinitionDB, EventLogDB
from ....common.event_instance import EventInstance
from ....common.event_definition import EventDefinition
from ....common.event_log import EventLog
from ....common.enums import EventInstanceStatus


class PostgreSQLEventInstanceRepository(EventInstanceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_ready_tasks(self) -> List[EventInstance]:
        # 使用 PostgreSQL 特有的数组函数和高效 JOIN 查询
        stmt = select(EventInstanceDB).where(
            EventInstanceDB.status == EventInstanceStatus.PENDING
        ).outerjoin(
            EventInstanceDB, 
            EventInstanceDB.id == func.any(EventInstanceDB.depends_on)
        ).group_by(
            EventInstanceDB.id
        ).having(
            or_(
                # 无依赖
                EventInstanceDB.depends_on == None,
                # 有依赖且所有依赖都已完成
                and_(
                    func.cardinality(EventInstanceDB.depends_on) > 0,
                    func.count(EventInstanceDB.id) == func.cardinality(EventInstanceDB.depends_on),
                    func.bool_and(EventInstanceDB.status == EventInstanceStatus.SUCCESS)
                )
            )
        )
        
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]

    async def find_pending_with_deps_satisfied(self) -> List[EventInstance]:
        # 该方法与 find_ready_tasks 功能相同，复用实现
        return await self.find_ready_tasks()

    async def update_fields(self, instance_id: str, fields: Dict[str, Any]) -> None:
        stmt = (
            update(EventInstanceDB)
            .where(EventInstanceDB.id == instance_id)
            .values(**fields)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def update(self, instance_id: str, fields: Dict[str, Any]) -> None:
        # 新增方法：更新指定字段
        stmt = (
            update(EventInstanceDB)
            .where(EventInstanceDB.id == instance_id)
            .values(**fields)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def increment_completed_children(self, parent_id: str) -> int:
        stmt = (
            update(EventInstanceDB)
            .where(EventInstanceDB.id == parent_id)
            .values(completed_children=EventInstanceDB.completed_children + 1)
            .returning(EventInstanceDB.completed_children)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def bulk_update_signal_by_path(
        self,
        trace_id: str,
        path_pattern: str,
        signal: str
    ) -> None:
        """
        批量更新指定路径模式下的所有事件实例的控制信号
        """
        stmt = (
            update(EventInstanceDB)
            .where(
                and_(
                    EventInstanceDB.trace_id == trace_id,
                    EventInstanceDB.node_path.like(path_pattern)
                )
            )
            .values(control_signal=signal)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def update_signal_by_trace(
        self,
        trace_id: str,
        signal: str
    ) -> None:
        """
        更新指定trace下所有事件实例的控制信号
        """
        stmt = (
            update(EventInstanceDB)
            .where(EventInstanceDB.trace_id == trace_id)
            .values(control_signal=signal)
        )
        await self.session.execute(stmt)
        await self.session.commit()

    def _to_domain(self, db: EventInstanceDB) -> EventInstance:
        from ....common.enums import ActorType, ScheduleType
        return EventInstance(
            id=db.id,
            trace_id=db.trace_id,
            parent_id=db.parent_id,
            job_id=db.job_id,
            def_id=db.def_id,
            node_path=db.node_path,
            depth=db.depth,
            actor_type=ActorType(db.actor_type),
            role=db.role,
            layer=db.layer,
            is_leaf_agent=db.is_leaf_agent,
            schedule_type=ScheduleType(db.schedule_type),
            round_index=db.round_index,
            cron_trigger_time=db.cron_trigger_time,
            status=EventInstanceStatus(db.status),
            progress=db.progress,
            control_signal=db.control_signal,
            depends_on=db.depends_on if db.depends_on else None,
            split_count=db.split_count,
            completed_children=db.completed_children,
            input_params=db.input_params if db.input_params else {},
            input_ref=db.input_ref,
            output_ref=db.output_ref,
            error_msg=db.error_msg,
            started_at=db.started_at,
            finished_at=db.finished_at,
            created_at=db.created_at,
            updated_at=db.updated_at
        )

    async def create(self, instance: EventInstance) -> None: 
        db_instance = EventInstanceDB(
            id=instance.id,
            trace_id=instance.trace_id,
            parent_id=instance.parent_id,
            job_id=instance.job_id,
            def_id=instance.def_id,
            actor_type=instance.actor_type,
            role=instance.role,
            layer=instance.layer,
            is_leaf_agent=instance.is_leaf_agent,
            schedule_type=instance.schedule_type,
            round_index=instance.round_index,
            cron_trigger_time=instance.cron_trigger_time,
            status=instance.status.value,
            node_path=instance.node_path,
            depth=instance.depth,
            progress=instance.progress,
            control_signal=instance.control_signal,
            depends_on=instance.depends_on,
            split_count=instance.split_count,
            completed_children=instance.completed_children,
            input_params=instance.input_params,
            input_ref=instance.input_ref,
            output_ref=instance.output_ref,
            error_msg=instance.error_msg,
            started_at=instance.started_at,
            finished_at=instance.finished_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at
        )
        self.session.add(db_instance)
        await self.session.commit()
    
    async def get(self, instance_id: str) -> Optional[EventInstance]: 
        stmt = select(EventInstanceDB).where(EventInstanceDB.id == instance_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None
    
    async def get_by_ids(self, ids: List[str]) -> List[EventInstance]: 
        stmt = select(EventInstanceDB).where(EventInstanceDB.id.in_(ids))
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def find_by_trace_id(self, trace_id: str) -> List[EventInstance]: 
        stmt = select(EventInstanceDB).where(EventInstanceDB.trace_id == trace_id)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def find_by_trace_id_with_filters(self, trace_id: str, filters: dict, limit: int = 100, offset: int = 0) -> List[EventInstance]:
        stmt = select(EventInstanceDB).where(EventInstanceDB.trace_id == trace_id)
        
        for key, value in filters.items():
            column = getattr(EventInstanceDB, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
        
        stmt = stmt.offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def lock_for_execution(self, instance_id: str, worker_id: str) -> bool: 
        # 使用 PostgreSQL 特有的 SELECT ... FOR UPDATE SKIP LOCKED
        stmt = (
            update(EventInstanceDB)
            .where(
                and_(
                    EventInstanceDB.id == instance_id,
                    EventInstanceDB.status == EventInstanceStatus.PENDING
                )
            )
            .values(
                status=EventInstanceStatus.RUNNING,
                job_id=worker_id
            )
            .returning(EventInstanceDB.id)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none() is not None
    
    async def update_status(self, instance_id: str, status: EventInstanceStatus, **kwargs) -> None: 
        update_data = {'status': status.value}
        update_data.update(kwargs)
        
        stmt = (
            update(EventInstanceDB)
            .where(EventInstanceDB.id == instance_id)
            .values(**update_data)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def bulk_update_status_by_trace(self, trace_id: str, status: EventInstanceStatus) -> None: 
        stmt = (
            update(EventInstanceDB)
            .where(EventInstanceDB.trace_id == trace_id)
            .values(status=status.value)
        )
        await self.session.execute(stmt)
        await self.session.commit()


class PostgreSQLEventDefinitionRepository(EventDefinitionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    def _to_domain(self, db: EventDefinitionDB) -> EventDefinition:
        from ....common.enums import ActorType, ScheduleType, NodeType
        return EventDefinition(
            id=db.id,
            name=db.name,
            node_type=NodeType(db.node_type),
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
            default_timeout=db.default_timeout,
            retry_policy=db.retry_policy or {"max_retries": 3, "backoff": "exponential"},
            ui_config=db.ui_config or {"icon": "robot", "color": "#FF0000"},
            is_active=db.is_active,
            created_at=db.created_at
        )
    
    async def get(self, def_id: str) -> EventDefinition:
        stmt = select(EventDefinitionDB).where(EventDefinitionDB.id == def_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None
    
    async def list_active_cron(self) -> List[EventDefinition]:
        stmt = select(EventDefinitionDB).where(
            EventDefinitionDB.is_active == True,
            EventDefinitionDB.cron_expr != None
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    
    async def get_by_job_id(self, job_id: str) -> EventDefinition:
        stmt = select(EventDefinitionDB).where(EventDefinitionDB.id == job_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None
    
    async def update_last_triggered_at(self, def_id: str, timestamp: datetime) -> None:
        stmt = (
            update(EventDefinitionDB)
            .where(EventDefinitionDB.id == def_id)
            .values(last_triggered_at=timestamp)
        )
        await self.session.execute(stmt)
        await self.session.commit()
    
    async def create(self, definition: EventDefinition) -> None:
        db_definition = EventDefinitionDB(
            id=definition.id,
            name=definition.name,
            node_type=definition.node_type.value,
            actor_type=definition.actor_type.value,
            role=definition.role,
            code_ref=definition.code_ref,
            entrypoint=definition.entrypoint,
            schedule_type=definition.schedule_type.value,
            cron_expr=definition.cron_expr,
            loop_config=definition.loop_config,
            resource_profile=definition.resource_profile,
            strategy_tags=definition.strategy_tags,
            default_params=definition.default_params,
            default_timeout=definition.default_timeout,
            retry_policy=definition.retry_policy,
            ui_config=definition.ui_config,
            is_active=definition.is_active,
            created_at=definition.created_at
        )
        self.session.add(db_definition)
        await self.session.commit()


class PostgreSQLEventLogRepository(EventLogRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    def _to_domain(self, db: EventLogDB) -> EventLog:
        return EventLog(
            id=db.id,
            instance_id=db.instance_id,
            trace_id=db.trace_id,
            event_type=db.event_type,
            level=db.level,
            content=db.content,
            payload_snapshot=db.payload_snapshot,
            execution_node=db.execution_node,
            agent_id=db.agent_id,
            created_at=db.created_at
        )

    async def create(self, log: EventLog) -> None:
        db_log = EventLogDB(
            id=log.id,
            instance_id=log.instance_id,
            trace_id=log.trace_id,
            event_type=log.event_type,
            level=log.level,
            content=log.content,
            payload_snapshot=log.payload_snapshot,
            execution_node=log.execution_node,
            agent_id=log.agent_id,
            created_at=log.created_at
        )
        self.session.add(db_log)
        await self.session.commit()

    async def get(self, log_id: str) -> EventLog:
        stmt = select(EventLogDB).where(EventLogDB.id == log_id)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

    async def find_by_instance_id(self, instance_id: str) -> List[EventLog]:
        stmt = select(EventLogDB).where(EventLogDB.instance_id == instance_id).order_by(EventLogDB.created_at)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]

    async def find_by_trace_id(self, trace_id: str) -> List[EventLog]:
        stmt = select(EventLogDB).where(EventLogDB.trace_id == trace_id).order_by(EventLogDB.created_at)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]

    async def find_by_trace_id_with_filters(self, trace_id: str, filters: dict, limit: int = 100, offset: int = 0) -> List[EventLog]:
        stmt = select(EventLogDB).where(EventLogDB.trace_id == trace_id)
        
        for key, value in filters.items():
            column = getattr(EventLogDB, key, None)
            if column is not None:
                stmt = stmt.where(column == value)
        
        stmt = stmt.order_by(EventLogDB.created_at).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]

    async def count_by_event_type(self, instance_id: str, event_type: str) -> int:
        stmt = select(func.count(EventLogDB.id)).where(
            and_(
                EventLogDB.instance_id == instance_id,
                EventLogDB.event_type == event_type
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
