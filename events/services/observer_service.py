import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any, Callable
from ..external.db.base import TaskInstanceRepository
from ..external.events.base import EventPublisher
from ..common.task_instance import TaskInstance
from ..common.enums import TaskInstanceStatus
from ..common.events import (
    TaskStatusEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TraceCancelledEvent,
    LoopRoundStartedEvent
)


class ObserverService:
    def __init__(
        self,
        inst_repo: TaskInstanceRepository,
        event_publisher: EventPublisher,
        webhook_registry: Optional[Any] = None  # 可选的 Webhook 注册表
    ):
        self.inst_repo = inst_repo
        self.event_publisher = event_publisher
        self.webhook_registry = webhook_registry

    async def on_task_status_changed(self, task: TaskInstance) -> None:
        """处理任务状态变更事件"""
        # 创建并发布任务状态事件
        event = TaskStatusEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            status=task.status.value,
            output_ref=task.output_ref,
            error_msg=task.error_msg,
            timestamp=datetime.utcnow()
        )
        
        # 发布到事件总线
        await self.event_publisher.publish("task.status.changed", event.model_dump())
        
        # 根据具体状态发布更细粒度的事件
        if task.status == TaskInstanceStatus.RUNNING:
            await self._publish_task_started(task)
        elif task.status == TaskInstanceStatus.SUCCESS:
            await self._publish_task_completed(task)
        elif task.status == TaskInstanceStatus.FAILED:
            await self._publish_task_failed(task)
        
        # 异步推送 Webhook（如果配置了）
        if self.webhook_registry:
            await self._send_webhook_if_configured(task.trace_id, event)

    async def _publish_task_started(self, task: TaskInstance) -> None:
        """发布任务开始事件"""
        event = TaskStartedEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            worker_id=task.job_id,
            timestamp=datetime.utcnow()
        )
        await self.event_publisher.publish("task.started", event.model_dump())

    async def _publish_task_completed(self, task: TaskInstance) -> None:
        """发布任务完成事件"""
        event = TaskCompletedEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            output_ref=task.output_ref or "",
            timestamp=datetime.utcnow()
        )
        await self.event_publisher.publish("task.completed", event.model_dump())

    async def _publish_task_failed(self, task: TaskInstance) -> None:
        """发布任务失败事件"""
        event = TaskFailedEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            error_msg=task.error_msg or "Unknown error",
            timestamp=datetime.utcnow()
        )
        await self.event_publisher.publish("task.failed", event.model_dump())

    async def on_trace_cancelled(self, trace_id: str, reason: Optional[str] = None) -> None:
        """处理 Trace 取消事件"""
        event = TraceCancelledEvent(
            trace_id=trace_id,
            reason=reason,
            timestamp=datetime.utcnow()
        )
        await self.event_publisher.publish("trace.cancelled", event.model_dump())

    async def on_loop_round_started(self, task: TaskInstance) -> None:
        """处理 LOOP 轮次开始事件"""
        event = LoopRoundStartedEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            round_index=task.round_index or 0,
            timestamp=datetime.utcnow()
        )
        await self.event_publisher.publish("loop.round_started", event.model_dump())

    async def _send_webhook_if_configured(self, trace_id: str, event: Any) -> None:
        """异步发送 Webhook（如果配置了）"""
        try:
            hooks = await self.webhook_registry.get_hooks(trace_id)
            for hook in hooks:
                asyncio.create_task(self._send_webhook(hook.url, event.model_dump()))
        except Exception as e:
            # 记录日志但不阻塞主流程
            print(f"Failed to send webhook: {e}")

    async def _send_webhook(self, url: str, event_data: Dict[str, Any]) -> None:
        """发送 Webhook 实现"""
        # TODO: 实现 Webhook 发送逻辑
        # 可以使用 aiohttp 或 httpx 库发送 HTTP 请求
        print(f"Sending webhook to {url}: {event_data}")

    # 保留原有的查询方法，兼容现有代码
    async def get_task_instance(self, task_id: str) -> Optional[TaskInstance]:
        return await self.inst_repo.get(task_id)

    async def get_trace_instances(self, trace_id: str) -> List[TaskInstance]:
        return await self.inst_repo.find_by_trace_id(trace_id)

    async def get_trace_status_summary(self, trace_id: str) -> dict:
        instances = await self.inst_repo.find_by_trace_id(trace_id)
        
        summary = {
            "trace_id": trace_id,
            "total": len(instances),
            "pending": 0,
            "running": 0,
            "success": 0,
            "failed": 0,
            "cancelled": 0,
            "skipped": 0,
            "layers": set(),
            "depth": 0
        }

        for instance in instances:
            status = instance.status.value
            if status in summary:
                summary[status] += 1
            summary["layers"].add(instance.layer)
            if instance.depth > summary["depth"]:
                summary["depth"] = instance.depth

        summary["layers"] = len(summary["layers"])
        summary["is_complete"] = summary["success"] + summary["failed"] + summary["cancelled"] + summary["skipped"] == summary["total"]
        
        return summary

    async def get_ready_tasks(self) -> List[TaskInstance]:
        return await self.inst_repo.find_ready_tasks()