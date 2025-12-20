import asyncio
import json
from typing import Dict, Any, Callable
from aio_pika import connect_robust, IncomingMessage, Message
from aio_pika.abc import AbstractQueue, AbstractExchange
from .base import MessageBroker


class RabbitMQDelayedMessageBroker(MessageBroker):
    def __init__(self, url: str = "amqp://guest:guest@localhost:5672/"):
        self.url = url
        self.connection = None
        self.channel = None
        self.exchanges = {}
        self.queues = {}

    async def connect(self):
        self.connection = await connect_robust(self.url)
        self.channel = await self.connection.channel()

    async def close(self):
        if self.channel:
            await self.channel.close()
        if self.connection:
            await self.connection.close()

    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        if not self.channel:
            await self.connect()

        exchange = await self._get_exchange(topic)
        await exchange.publish(
            Message(body=json.dumps(message).encode()),
            routing_key=topic
        )

    async def publish_delayed(self, topic: str, message: Dict[str, Any], delay_sec: int) -> None:
        if not self.channel:
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
        if not self.channel:
            await self.connect()

        queue = await self._get_queue(topic)
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    msg_data = json.loads(message.body.decode())
                    await handler(msg_data)

    async def _get_exchange(self, topic: str) -> AbstractExchange:
        if topic not in self.exchanges:
            self.exchanges[topic] = await self.channel.declare_exchange(
                name=topic,
                type="direct",
                durable=True
            )
        return self.exchanges[topic]

    async def _get_delayed_exchange(self, topic: str) -> AbstractExchange:
        delayed_topic = f"{topic}.delayed"
        if delayed_topic not in self.exchanges:
            self.exchanges[delayed_topic] = await self.channel.declare_exchange(
                name=delayed_topic,
                type="x-delayed-message",
                durable=True,
                arguments={"x-delayed-type": "direct"}
            )
        return self.exchanges[delayed_topic]

    async def _get_queue(self, topic: str) -> AbstractQueue:
        if topic not in self.queues:
            exchange = await self._get_exchange(topic)
            self.queues[topic] = await self.channel.declare_queue(
                name=topic,
                durable=True
            )
            await self.queues[topic].bind(exchange, routing_key=topic)
        return self.queues[topic]