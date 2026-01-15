import asyncio
import json
import logging
from typing import Dict, Any, Callable
from aio_pika import connect_robust, IncomingMessage, Message
from aio_pika.abc import AbstractQueue, AbstractExchange
from .base import MessageBroker

logger = logging.getLogger(__name__)


class RabbitMQDelayedMessageBroker(MessageBroker):
    def __init__(self, url: str = "amqp://guest:guest@localhost:5672/"):
        self.url = url
        self.connection = None
        self.channel = None
        self.exchanges: Dict[str, AbstractExchange] = {}
        self.queues: Dict[str, AbstractQueue] = {}
        self._lock = asyncio.Lock()  # 添加锁保护并发访问

    async def connect(self):
        if self.connection is None or self.connection.is_closed:
            self.connection = await connect_robust(self.url)
            self.channel = await self.connection.channel()
            logger.info("RabbitMQ connection established")

    async def close(self):
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()

    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        async with self._lock:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            exchange = await self._get_exchange(topic)
            # 确保 queue 存在并绑定到 exchange，避免消息在没有消费者时丢失
            await self._get_queue(topic)

        await exchange.publish(
            Message(body=json.dumps(message).encode()),
            routing_key=topic
        )
        logger.debug(f"Published message to {topic}")

    async def publish_delayed(self, topic: str, message: Dict[str, Any], delay_sec: int) -> None:
        async with self._lock:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            # 使用 RabbitMQ 延时插件，通过 x-delay 头实现延时
            exchange = await self._get_delayed_exchange(topic)

        await exchange.publish(
            Message(
                body=json.dumps(message).encode(),
                headers={"x-delay": delay_sec * 1000}  # 转换为毫秒
            ),
            routing_key=topic
        )

    async def consume(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> None:
        async with self._lock:
            if not self.channel or self.channel.is_closed:
                await self.connect()

            queue = await self._get_queue(topic)

        logger.info(f"Starting consumer for topic: {topic}")
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        msg_data = json.loads(message.body.decode())
                        await handler(msg_data)
                    except Exception as e:
                        logger.error(f"Error processing message from {topic}: {e}")

    async def _get_exchange(self, topic: str) -> AbstractExchange:
        """获取或创建 exchange（调用前需持有锁）"""
        if topic not in self.exchanges:
            self.exchanges[topic] = await self.channel.declare_exchange(
                name=topic,
                type="direct",
                durable=True
            )
            logger.debug(f"Declared exchange: {topic}")
        return self.exchanges[topic]

    async def _get_delayed_exchange(self, topic: str) -> AbstractExchange:
        """获取或创建延时 exchange（调用前需持有锁）"""
        delayed_topic = f"{topic}.delayed"
        if delayed_topic not in self.exchanges:
            self.exchanges[delayed_topic] = await self.channel.declare_exchange(
                name=delayed_topic,
                type="x-delayed-message",
                durable=True,
                arguments={"x-delayed-type": "direct"}
            )
            logger.debug(f"Declared delayed exchange: {delayed_topic}")
        return self.exchanges[delayed_topic]

    async def _get_queue(self, topic: str) -> AbstractQueue:
        """获取或创建 queue 并绑定到 exchange（调用前需持有锁）"""
        if topic not in self.queues:
            exchange = await self._get_exchange(topic)
            self.queues[topic] = await self.channel.declare_queue(
                name=topic,
                durable=True
            )
            await self.queues[topic].bind(exchange, routing_key=topic)
            logger.debug(f"Declared and bound queue: {topic}")
        return self.queues[topic]