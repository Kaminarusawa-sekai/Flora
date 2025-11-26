# repositories/rabbitmq_repo.py
import pika
import json
import logging
from typing import Dict, Optional
from .loop_task_repo import LoopTask, LoopTaskRepository

class RabbitMQTaskRepository(LoopTaskRepository):
    def __init__(self, rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"):
        self.rabbitmq_url = rabbitmq_url
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.BlockingChannel] = None
        self._setup_rabbitmq()

    def _get_connection(self):
        if self._connection is None or self._connection.is_closed:
            self._connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
        return self._connection

    def _get_channel(self):
        conn = self._get_connection()
        if self._channel is None or self._channel.is_closed:
            self._channel = conn.channel()
            self._declare_exchanges_and_queues()
        return self._channel

    def _declare_exchanges_and_queues(self):
        channel = self._channel
        # 延迟交换器（需安装 rabbitmq-delayed-message-exchange 插件）
        channel.exchange_declare(
            exchange='loop.delayed',
            exchange_type='x-delayed-message',
            arguments={'x-delayed-type': 'direct'}
        )
        # 触发队列
        channel.queue_declare(queue='loop.trigger.queue', durable=True)
        channel.queue_bind(
            queue='loop.trigger.queue',
            exchange='loop.delayed',
            routing_key='trigger'
        )

    def save_task(self, task: LoopTask) -> None:
        """注册任务：发送一条带 delay 的消息"""
        channel = self._get_channel()
        delay_ms = int((task.next_run_at - time.time()) * 1000)
        if delay_ms < 0:
            delay_ms = 0

        message_body = json.dumps({
            "task_id": task.task_id,
            "target_actor_address": task.target_actor_address,
            "message": task.message,
            "interval_sec": task.interval_sec,
            "is_active": task.is_active
        })

        channel.basic_publish(
            exchange='loop.delayed',
            routing_key='trigger',
            body=message_body,
            properties=pika.BasicProperties(
                delivery_mode=2,  # persistent
                headers={'x-delay': delay_ms}
            )
        )
        logging.info(f"Published delayed task {task.task_id} with delay {delay_ms}ms")

    def load_task(self, task_id: str) -> Optional[LoopTask]:
        # RabbitMQ 不支持随机读取，此方法在延迟模式下无意义
        # 可配合数据库使用，此处返回 None
        return None

    def delete_task(self, task_id: str) -> bool:
        # RabbitMQ 无法取消已发送的延迟消息
        # 实际做法：在消费时检查任务是否已被取消（需额外状态存储）
        # 简化处理：返回 False，建议结合 DB 使用
        logging.warning("RabbitMQ repo does not support delete_task")
        return False

    def list_active_tasks(self) -> Dict[str, LoopTask]:
        # 同上，RabbitMQ 无法列出 pending 消息
        return {}

    def update_next_run(self, task_id: str, next_run_at: float) -> bool:
        # 不支持，需重新注册新消息
        return False

    def close(self):
        if self._channel:
            self._channel.close()
        if self._connection:
            self._connection.close()