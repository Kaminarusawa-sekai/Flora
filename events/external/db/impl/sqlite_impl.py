from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from ..base import EventInstanceRepository, EventDefinitionRepository, EventLogRepository, AgentTaskHistoryRepository, AgentDailyMetricRepository
from ..models import EventInstanceDB, EventDefinitionDB, EventLogDB, AgentTaskHistory, AgentDailyMetric
from common.event_instance import EventInstance
from common.event_definition import EventDefinition
from common.event_log import EventLog
from common.enums import EventInstanceStatus, ActorType

logger = logging.getLogger(__name__)
class SQLiteEventInstanceRepository(EventInstanceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_ready_tasks(self) -> List[EventInstance]:
        # SQLite 不支持复杂的 array 函数和 JOIN 查询，使用 N+1 查询方式
        # 先查所有 PENDING 状态的事件
        stmt = select(EventInstanceDB).where(EventInstanceDB.status == EventInstanceStatus.PENDING)
        result = await self.session.execute(stmt)
        pending_tasks = result.scalars().all()
        ready = []

        for task_db in pending_tasks:
            deps = task_db.depends_on or []
            if not deps:
                # 无依赖，直接就绪
                ready.append(self._to_domain(task_db))
            else:
                # 查依赖事件状态
                dep_ids = [d for d in deps]  # 假设 depends_on 是 list[str]
                dep_stmt = select(EventInstanceDB).where(EventInstanceDB.id.in_(dep_ids))
                dep_result = await self.session.execute(dep_stmt)
                dep_map = {d.id: d.status for d in dep_result.scalars()}
                
                # 检查所有依赖是否都已成功
                all_deps_success = True
                for dep_id in deps:
                    if dep_map.get(dep_id) != EventInstanceStatus.SUCCESS:
                        all_deps_success = False
                        break
                
                if all_deps_success:
                    ready.append(self._to_domain(task_db))
        return ready

    async def find_pending_with_deps_satisfied(self) -> List[EventInstance]:
        # 该方法与 find_ready_tasks 功能相同，复用实现
        return await self.find_ready_tasks()

    async def update_fields(
        self, 
            instance_id: str, 
            fields: Optional[Dict[str, Any]] = None,
            **kwargs
        ) -> None:
            # 合并 fields 和 kwargs
            all_updates = {**(fields or {}), **kwargs}
            if not all_updates:
                return
            
            stmt = (
                update(EventInstanceDB)
                .where(EventInstanceDB.id == instance_id)
                .values(**all_updates)
            )
            await self.session.execute(stmt)
            await self.session.commit()
    
    async def get_by_task_id(self, task_id: str) -> Optional[EventInstance]:
        """
        根据 task_id 获取事件实例
        """
        stmt = select(EventInstanceDB).where(EventInstanceDB.task_id == task_id).limit(1)
        result = await self.session.execute(stmt)
        row = result.scalar_one_or_none()
        return self._to_domain(row) if row else None

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

    async def upsert_by_task_id(self, task_id: str, trace_id: str, **fields) -> str:
        """
        根据 task_id 执行 upsert 操作
        如果存在则更新，不存在则创建（挂载到根节点下）
        返回操作后的实例 ID
        """
        import uuid
        from datetime import datetime, timezone
        
        # 1. 尝试更新
        stmt = (
            update(EventInstanceDB)
            .where(EventInstanceDB.task_id == task_id)
            .values(**fields)
        )
        result = await self.session.execute(stmt)
        
        if result.rowcount > 0:
            # 更新成功，获取实例 ID
            get_stmt = select(EventInstanceDB.id).where(EventInstanceDB.task_id == task_id)
            get_result = await self.session.execute(get_stmt)
            return get_result.scalar_one()
        
        # 2. 更新失败，说明需要创建新实例
        # 查找根节点
        root_stmt = (
            select(EventInstanceDB)
            .where(
                EventInstanceDB.trace_id == trace_id,
                EventInstanceDB.parent_id == None
            )
            .limit(1)
        )
        root_res = await self.session.execute(root_stmt)
        root_node = root_res.scalar_one_or_none()
        
        if not root_node:
            raise ValueError(f"Trace {trace_id} has no root node")
        
        # 3. 创建新实例
        new_id = str(uuid.uuid4())
        new_instance = EventInstanceDB(
            id=new_id,
            task_id=task_id,
            trace_id=trace_id,
            parent_id=root_node.task_id,
            node_path=f"{root_node.node_path}{root_node.task_id}/",
            depth=root_node.depth + 1,
            
            # 从fields中获取值，或者使用默认值
            actor_type=fields.get("actor_type", "AGENT"),
            def_id=fields.get("def_id", "dynamic_task"),
            status=fields.get("status", EventInstanceStatus.PENDING.value),
            user_id=root_node.user_id,
            
            # 设置时间字段
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            started_at=fields.get("started_at"),
            finished_at=fields.get("finished_at"),
            
            # 其他可选字段
            worker_id=fields.get("worker_id"),
            input_params=fields.get("input_params"),
            runtime_state_snapshot=fields.get("runtime_state_snapshot"),
            progress=fields.get("progress", 0),
            error_detail=fields.get("error_detail")
        )
        
        self.session.add(new_instance)
        await self.session.commit()
        return new_id

    def _to_domain(self, db: EventInstanceDB) -> EventInstance:
        return EventInstance(
            id=db.id,
            trace_id=db.trace_id,
            task_id=db.task_id,
            request_id=db.request_id,
            parent_id=db.parent_id,
            def_id=db.def_id,
            user_id=db.user_id,
            worker_id=db.worker_id,
            name=db.name,
            node_path=db.node_path,
            depth=db.depth,
            actor_type=ActorType(db.actor_type),
            role=db.role,
            layer=db.layer,
            is_leaf_agent=db.is_leaf_agent,
            status=db.status,
            progress=db.progress,
            control_signal=db.control_signal,
            depends_on=db.depends_on if db.depends_on else None,
            split_count=db.split_count,
            completed_children=db.completed_children,
            input_params=db.input_params if db.input_params else {},
            input_ref=db.input_ref,
            output_ref=db.output_ref,
            error_detail=db.error_detail,
            runtime_state_snapshot=db.runtime_state_snapshot,
            result_summary=db.result_summary,
            interactive_signal=db.interactive_signal,
            started_at=db.started_at,
            finished_at=db.finished_at,
            created_at=db.created_at,
            updated_at=db.updated_at
        )

    async def create(self, instance: EventInstance) -> None: 
        db_instance = EventInstanceDB(
            id=instance.id,
            task_id=instance.task_id,
            trace_id=instance.trace_id,
            request_id=instance.request_id,
            parent_id=instance.parent_id,
            def_id=instance.def_id,
            user_id=instance.user_id,
            worker_id=instance.worker_id,
            name=instance.name,
            actor_type=instance.actor_type,
            role=instance.role,
            layer=instance.layer,
            is_leaf_agent=instance.is_leaf_agent,
            status=instance.status,
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
            error_detail=instance.error_detail,
            runtime_state_snapshot=instance.runtime_state_snapshot,
            result_summary=instance.result_summary,
            interactive_signal=instance.interactive_signal,
            started_at=instance.started_at,
            finished_at=instance.finished_at,
            created_at=instance.created_at,
            updated_at=instance.updated_at
        )
        self.session.add(db_instance)
        await self.session.commit()

    async def bulk_create(self, instances: List[EventInstance]) -> None:
        """
        批量创建事件实例
        """
        if not instances:
            return
        
        # 转换为数据库模型列表
        db_instances = []
        for instance in instances:
            db_instance = EventInstanceDB(
                id=instance.id,
                task_id=instance.task_id,
                trace_id=instance.trace_id,
                request_id=instance.request_id,
                parent_id=instance.parent_id,
                def_id=instance.def_id,
                user_id=instance.user_id,
                worker_id=instance.worker_id,
                name=instance.name,
                actor_type=instance.actor_type,
                role=instance.role,
                layer=instance.layer,
                is_leaf_agent=instance.is_leaf_agent,
                status=instance.status,
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
                error_detail=instance.error_detail,
                runtime_state_snapshot=instance.runtime_state_snapshot,
                result_summary=instance.result_summary,
                interactive_signal=instance.interactive_signal,
                started_at=instance.started_at,
                finished_at=instance.finished_at,
                created_at=instance.created_at,
                updated_at=instance.updated_at
            )
            db_instances.append(db_instance)
        
        # 批量添加到会话
        self.session.add_all(db_instances)
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
        # SQLite 不支持 SELECT ... FOR UPDATE SKIP LOCKED，直接更新状态
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
    
    async def find_traces_by_user_id(self, user_id: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None, limit: int = 100, offset: int = 0) -> List[dict]:
        """
        根据user_id查询所有trace_id及其状态
        
        Args:
            user_id: 用户ID
            start_time: 开始时间
            end_time: 结束时间
            limit: 每页数量
            offset: 偏移量
            
        Returns:
            List[dict]: trace_id列表及其状态信息
        """
        # 使用SQLite兼容的查询方式
        # 1. 首先获取所有唯一的trace_id
        stmt = select(EventInstanceDB.trace_id).distinct().where(EventInstanceDB.user_id == user_id)
        
        # 添加时间范围过滤
        if start_time:
            stmt = stmt.where(EventInstanceDB.created_at >= start_time)
        if end_time:
            stmt = stmt.where(EventInstanceDB.created_at <= end_time)
        
        # 排序并分页
        stmt = stmt.order_by(EventInstanceDB.created_at.desc()).limit(limit).offset(offset)
        
        result = await self.session.execute(stmt)
        trace_ids = [row.trace_id for row in result.all()]
        
        traces = []
        for trace_id in trace_ids:
            # 2. 对于每个trace_id，获取最新状态
            # 查询该trace下的所有实例
            trace_stmt = select(EventInstanceDB).where(
                EventInstanceDB.trace_id == trace_id,
                EventInstanceDB.user_id == user_id
            ).order_by(EventInstanceDB.updated_at.desc())
            
            trace_result = await self.session.execute(trace_stmt)
            instances = trace_result.scalars().all()
            
            if instances:
                # 获取最新状态
                latest_instance = instances[0]
                traces.append({
                    "trace_id": trace_id,
                    "created_at": latest_instance.created_at,
                    "status": latest_instance.status
                })
        
        return traces


class SQLiteEventDefinitionRepository(EventDefinitionRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
        logger.info(f"Using SQLite database: {session}")

    
    def _to_domain(self, db: EventDefinitionDB) -> EventDefinition:
        return EventDefinition(
            id=db.id,
            name=db.name,
            user_id=db.user_id,
            node_type=db.node_type,
            actor_type=db.actor_type,
            role=db.role,
            is_active=db.is_active,
            created_at=db.created_at
        )
    
    async def get(self, def_id: str) -> EventDefinition:
        stmt = select(EventDefinitionDB).where(EventDefinitionDB.id == def_id)
        logger.info(f"Getting event definition {def_id} from session {self.session}")
        result = await self.session.execute(stmt)
        row = result.unique().scalar_one_or_none()
        return self._to_domain(row) if row else None
    
    async def list_active_cron(self) -> List[EventDefinition]:
        stmt = select(EventDefinitionDB).where(
            EventDefinitionDB.is_active == True,
            EventDefinitionDB.cron_expr != None
        )
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        return [self._to_domain(row) for row in rows]
    

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
            user_id=definition.user_id,
            node_type=definition.node_type,
            actor_type=definition.actor_type,
            role=definition.role,
            is_active=definition.is_active,
            created_at=definition.created_at
        )
        self.session.add(db_definition)
        await self.session.commit()


class SQLiteEventLogRepository(EventLogRepository):
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
        stmt = select(EventLogDB).where(
            and_(
                EventLogDB.instance_id == instance_id,
                EventLogDB.event_type == event_type
            )
        )
        result = await self.session.execute(stmt)
        return len(result.scalars().all())


class SQLiteAgentTaskHistoryRepository(AgentTaskHistoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, history_data: dict) -> None:
        """
        将完成的任务写入数据库
        """
        # 转换时间格式
        start_time = history_data.get('start_time')
        end_time = history_data.get('end_time')
        
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time)
        
        # 计算持续时间
        duration_ms = history_data.get('duration_ms')
        if duration_ms is None and start_time and end_time:
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        record = AgentTaskHistory(
            agent_id=history_data['agent_id'],
            trace_id=history_data.get('trace_id', ''),
            task_id=history_data['task_id'],
            task_name=history_data.get('task_name'),
            status=history_data['status'],
            start_time=start_time,
            end_time=end_time,
            duration_ms=duration_ms,
            input_params=history_data.get('input_params'),
            output_result=history_data.get('output_result'),
            error_msg=history_data.get('error_msg')
        )
        
        self.session.add(record)
        await self.session.commit()

    async def get_recent_tasks(self, agent_id: str, limit: int = 20) -> List[dict]:
        """
        从数据库查询最近的历史记录
        """
        stmt = (
            select(AgentTaskHistory)
            .where(AgentTaskHistory.agent_id == agent_id)
            .order_by(AgentTaskHistory.created_at.desc())
            .limit(limit)
        )
        
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        
        # 转换为字典格式
        return [
            {
                'id': row.id,
                'agent_id': row.agent_id,
                'trace_id': row.trace_id,
                'task_id': row.task_id,
                'task_name': row.task_name,
                'status': row.status,
                'start_time': row.start_time.isoformat() if row.start_time else None,
                'end_time': row.end_time.isoformat() if row.end_time else None,
                'duration_ms': row.duration_ms,
                'input_params': row.input_params,
                'output_result': row.output_result,
                'error_msg': row.error_msg,
                'created_at': row.created_at.isoformat()
            }
            for row in rows
        ]

    async def get_task_statistics(self, agent_id: str, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
        """
        获取任务统计数据
        """
        stmt = select(
            func.count(AgentTaskHistory.id).label('total_tasks'),
            func.count(AgentTaskHistory.id).filter(AgentTaskHistory.status == 'COMPLETED').label('success_tasks'),
            func.count(AgentTaskHistory.id).filter(AgentTaskHistory.status == 'FAILED').label('failed_tasks'),
            func.avg(AgentTaskHistory.duration_ms).label('avg_duration_ms')
        ).where(AgentTaskHistory.agent_id == agent_id)
        
        if start_date:
            stmt = stmt.where(AgentTaskHistory.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AgentTaskHistory.created_at <= end_date)
        
        result = await self.session.execute(stmt)
        row = result.first()
        
        return {
            'total_tasks': row.total_tasks or 0,
            'success_tasks': row.success_tasks or 0,
            'failed_tasks': row.failed_tasks or 0,
            'avg_duration_ms': float(row.avg_duration_ms) if row.avg_duration_ms else 0.0
        }


class SQLiteAgentDailyMetricRepository(AgentDailyMetricRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def update_daily_metric(self, agent_id: str, date_str: str, status: str, duration_ms: int) -> None:
        """
        更新每日统计指标
        """
        # 先尝试获取现有记录
        stmt = (
            select(AgentDailyMetric)
            .where(
                AgentDailyMetric.agent_id == agent_id,
                AgentDailyMetric.date_str == date_str
            )
        )
        
        result = await self.session.execute(stmt)
        metric = result.scalar_one_or_none()
        
        if metric:
            # 更新现有记录
            metric.total_tasks += 1
            if status == 'COMPLETED':
                metric.success_tasks += 1
            elif status == 'FAILED':
                metric.failed_tasks += 1
            metric.total_duration_ms += duration_ms
        else:
            # 创建新记录
            metric = AgentDailyMetric(
                agent_id=agent_id,
                date_str=date_str,
                total_tasks=1,
                success_tasks=1 if status == 'COMPLETED' else 0,
                failed_tasks=1 if status == 'FAILED' else 0,
                total_duration_ms=duration_ms
            )
            self.session.add(metric)
        
        await self.session.commit()

    async def get_recent_metrics(self, agent_id: str, days: int = 7) -> List[dict]:
        """
        获取最近几天的统计指标
        """
        # 计算起始日期
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days-1)
        
        stmt = (
            select(AgentDailyMetric)
            .where(
                AgentDailyMetric.agent_id == agent_id,
                AgentDailyMetric.date_str >= start_date.isoformat(),
                AgentDailyMetric.date_str <= end_date.isoformat()
            )
            .order_by(AgentDailyMetric.date_str)
        )
        
        result = await self.session.execute(stmt)
        rows = result.scalars().all()
        
        # 转换为字典格式
        return [
            {
                'date_str': row.date_str,
                'total_tasks': row.total_tasks,
                'success_tasks': row.success_tasks,
                'failed_tasks': row.failed_tasks,
                'total_duration_ms': row.total_duration_ms,
                'avg_duration_ms': row.total_duration_ms / row.total_tasks if row.total_tasks > 0 else 0
            }
            for row in rows
        ]
