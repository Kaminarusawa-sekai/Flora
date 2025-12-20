import asyncio
from typing import Dict, Any
from ...external.messaging.base import MessageBroker
from ...services.lifecycle_service import LifecycleService
from ...external.db.session import async_session_factory, dialect
from ...external.db.impl import create_task_instance_repo


class TaskDispatcher:
    """
    任务分发器，负责消费任务执行消息并分发到相应的 Worker
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
        启动任务分发器，开始消费任务执行消息
        """
        await self.broker.consume("task.execute", self._handle_task_execute)

    async def _handle_task_execute(self, msg: Dict[str, Any]):
        """
        处理任务执行消息
        """
        task_id = msg["instance_id"]
        
        # 每次处理消息创建一个新的会话
        async with async_session_factory() as session:
            inst_repo = create_task_instance_repo(session, dialect)
            
            task = await inst_repo.get(task_id)
            
            if not task:
                return

            # 简化处理：跳过trace取消检查（暂未实现）
            # 简化处理：跳过依赖检查（暂未实现）

            # 简化处理：直接更新状态为RUNNING，然后调用Worker
            await inst_repo.update_status(task_id, "RUNNING")
            
            try:
                # 发布任务到消息队列，由Worker自己消费
                worker_payload = {
                    "instance_id": task.id,
                    "trace_id": task.trace_id,
                    "definition_id": task.definition_id,
                    "input_params": task.input_params
                }
                await self.broker.publish("worker.execute", worker_payload)
            except Exception as e:
                # 如果发布消息失败，更新任务状态为FAILED
                await inst_repo.update_status(
                    task_id, 
                    "FAILED", 
                    error_msg=f"Failed to publish task to worker queue: {str(e)}"
                )


async def task_execute_consumer(
    broker: MessageBroker
):
    """
    任务执行消息消费者（旧版兼容）
    """
    async def handler(msg: Dict[str, Any]):
        task_id = msg["instance_id"]
        
        # 每次处理消息创建一个新的会话
        async with async_session_factory() as session:
            inst_repo = create_task_instance_repo(session, dialect)
            
            task = await inst_repo.get(task_id)
            
            if not task:
                return

            # 简化处理：直接更新状态为RUNNING，然后调用Worker
            await inst_repo.update_status(task_id, "RUNNING")
            
            try:
                # 发布任务到消息队列，由Worker自己消费
                worker_payload = {
                    "instance_id": task.id,
                    "trace_id": task.trace_id,
                    "definition_id": task.definition_id,
                    "input_params": task.input_params
                }
                await broker.publish("worker.execute", worker_payload)
            except Exception as e:
                await inst_repo.update_status(
                    task_id, 
                    "FAILED", 
                    error_msg=f"Failed to publish task to worker queue: {str(e)}"
                )

    await broker.consume("task.execute", handler)