import asyncio
from typing import Dict, Any
from ...external.messaging.base import MessageBroker
from ...external.db.base import TaskInstanceRepository
from ...external.cache.redis_impl import redis_client
from ...services.lifecycle_service import LifecycleService


class TaskDispatcher:
    """
    任务分发器，负责消费任务执行消息并分发到相应的 Worker
    """

    def __init__(
        self,
        broker: MessageBroker,
        inst_repo: TaskInstanceRepository,
        lifecycle_service: LifecycleService,
        worker_url: str = "http://localhost:8001"
    ):
        self.broker = broker
        self.inst_repo = inst_repo
        self.lifecycle_service = lifecycle_service
        self.worker_url = worker_url

    async def start(self):
        """
        启动任务分发器，开始消费任务执行消息
        """
        await self.broker.consume("task.execute", self._handle_task_execute)

    async def _handle_task_execute(self, msg: Dict[str, Any]):
        """
        处理任务执行消息
        """
        task_id = msg["instance_id"]
        task = await self.inst_repo.get(task_id)

        # 检查 trace 是否被取消
        signal = await redis_client.get(f"trace_signal:{task.trace_id}")
        if signal == "CANCEL":
            return

        # 检查依赖（DAG）
        if task.depends_on:
            deps = await self.inst_repo.get_by_ids(task.depends_on)
            if any(d.status != "SUCCESS" for d in deps):
                # 5秒后重试
                await self.broker.publish_delayed("task.execute", msg, 5)
                return

        # 抢锁派发
        if await self.inst_repo.lock_for_execution(task_id, "worker-01"):
            # 模拟调用 Worker
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(f"{self.worker_url}/execute", json=task.model_dump())


async def task_execute_consumer(
    broker: MessageBroker, 
    inst_repo: TaskInstanceRepository, 
    worker_url: str
):
    """
    任务执行消息消费者（旧版兼容）
    """
    async def handler(msg: Dict[str, Any]):
        task_id = msg["instance_id"]
        task = await inst_repo.get(task_id)

        # 检查 trace 是否被取消
        from ...external.cache.redis_impl import redis_client
        signal = await redis_client.get(f"trace_signal:{task.trace_id}")
        if signal == "CANCEL":
            return

        # 检查依赖（DAG）
        if task.depends_on:
            deps = await inst_repo.get_by_ids(task.depends_on)
            if any(d.status != "SUCCESS" for d in deps):
                await broker.publish_delayed("task.execute", msg, 5)
                return

        # 抢锁派发
        if await inst_repo.lock_for_execution(task_id, "worker-01"):
            # 模拟调用 Worker
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(f"{worker_url}/execute", json=task.model_dump())

    await broker.consume("task.execute", handler)