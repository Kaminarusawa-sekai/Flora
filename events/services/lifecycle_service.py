import uuid
from datetime import datetime
from typing import Optional
from ..common.task_instance import TaskInstance
from ..common.enums import TaskInstanceStatus, ScheduleType
from ..external.db.base import TaskDefinitionRepository, TaskInstanceRepository
from ..external.messaging.base import MessageBroker
from ..external.cache.base import CacheClient


class LifecycleService:
    def __init__(
        self,
        def_repo: TaskDefinitionRepository,
        inst_repo: TaskInstanceRepository,
        broker: MessageBroker,
        cache: Optional[CacheClient] = None
    ):
        self.def_repo = def_repo
        self.inst_repo = inst_repo
        self.broker = broker
        self.cache = cache

    async def start_new_trace(
        self,
        def_id: str,
        input_params: dict,
        trigger_type: str = "MANUAL"
    ) -> str:
        # 输入校验：检查 def_id 是否 active
        definition = await self.def_repo.get(def_id)
        if not definition.is_active:
            raise ValueError(f"Task definition {def_id} is not active")
        
        trace_id = str(uuid.uuid4())
        job_id = f"job-{trace_id[:8]}"
        root_id = str(uuid.uuid4())

        root = TaskInstance(
            id=root_id,
            trace_id=trace_id,
            job_id=job_id,
            parent_id=None,
            actor_type=definition.actor_type,
            role=definition.role,
            layer=0,
            is_leaf_agent=(definition.actor_type == "AGENT" and not definition.role),  # 简化判断
            schedule_type=definition.schedule_type,
            round_index=0 if definition.schedule_type == ScheduleType.LOOP else None,
            cron_trigger_time=datetime.now(timezone.utc) if definition.schedule_type == ScheduleType.CRON else None,
            status=TaskInstanceStatus.PENDING,
            node_path="/",
            depth=0,
            depends_on=None,
            split_count=0,
            completed_children=0,
            input_params={**definition.default_params, **input_params},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        await self.inst_repo.create(root)
        await self._schedule_task(root)
        return trace_id

    async def handle_task_completed(self, task_id: str, output_ref: str):
        # 幂等性检查：任务已完成则直接返回
        task = await self.inst_repo.get(task_id)
        if task.status != TaskInstanceStatus.RUNNING:
            return
        
        # 更新任务状态为成功
        await self.inst_repo.update_status(
            task_id,
            TaskInstanceStatus.SUCCESS,
            output_ref=output_ref,
            finished_at=datetime.now(timezone.utc)
        )

        # 通知父节点计数
        if task.parent_id:
            new_count = await self.inst_repo.increment_completed_children(task.parent_id)
            parent = await self.inst_repo.get(task.parent_id)
            # 检查是否需要激活聚合器
            if parent.status == TaskInstanceStatus.PENDING and new_count >= parent.split_count:
                await self._activate_aggregator(parent)

        # LOOP 任务处理：检查是否需要下一轮
        if task.schedule_type == ScheduleType.LOOP:
            # 简化实现：假设 max_rounds 和 interval_sec 是配置项
            # 在实际实现中，应该从任务定义中获取这些配置
            max_rounds = 5  # 默认值，实际应从任务定义获取
            current_round = task.round_index or 0
            if current_round + 1 < max_rounds:
                # 重置任务状态为 PENDING，准备下一轮
                await self.inst_repo.update_fields(
                    task_id,
                    status=TaskInstanceStatus.PENDING,
                    round_index=current_round + 1,
                    started_at=None,
                    finished_at=None,
                    updated_at=datetime.now(timezone.utc)
                )
                # 延时派发下一轮任务
                interval = 10  # 默认值，实际应从任务定义获取
                await self.broker.publish_delayed(
                    "task.execute",
                    {"instance_id": task.id},
                    delay_sec=interval
                )

    async def handle_task_failed(self, task_id: str, error_msg: str):
        # 获取任务
        task = await self.inst_repo.get(task_id)
        if task.status != TaskInstanceStatus.RUNNING:
            return  # 幂等性检查
        
        # 更新任务状态为失败
        await self.inst_repo.update_status(
            task_id,
            TaskInstanceStatus.FAILED,
            error_msg=error_msg,
            finished_at=datetime.now(timezone.utc)
        )
        
        # 级联失败：将同 trace 下所有 PENDING 任务标记为 SKIPPED
        await self.inst_repo.bulk_update_status_by_trace(
            task.trace_id,
            TaskInstanceStatus.SKIPPED
        )
        
        # TODO: 触发告警事件（通过 ObserverService）
        # await self.observer_svc.on_task_status_changed(task)

    async def _activate_aggregator(self, parent: TaskInstance):
        # 激活聚合器：更新状态为 RUNNING 并派发执行
        await self.inst_repo.update_status(
            parent.id,
            TaskInstanceStatus.RUNNING,
            started_at=datetime.now(timezone.utc)
        )
        await self.broker.publish_delayed("task.execute", {"instance_id": parent.id}, delay_sec=0)

    async def _schedule_task(self, task: TaskInstance):
        # 统一入口：所有任务派发走 broker.publish_delayed，支持延时和重试
        await self.broker.publish_delayed("task.execute", {"instance_id": task.id}, delay_sec=0)