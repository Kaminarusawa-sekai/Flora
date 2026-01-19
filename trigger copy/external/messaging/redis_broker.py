import json
import asyncio
from typing import Callable, Any
from redis.asyncio import Redis
from .base import MessageBroker


class RedisMessageBroker(MessageBroker):
    """基于Redis的消息队列实现"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        self.redis_url = redis_url
        self.redis = None
    
    async def __aenter__(self):
        await self.connect()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def connect(self):
        """连接到Redis服务器"""
        self.redis = await Redis.from_url(self.redis_url, decode_responses=True)
    
    async def close(self):
        """关闭Redis连接"""
        if self.redis:
            await self.redis.close()
    
    async def publish(self, topic: str, message: dict) -> None:
        """发送消息到指定主题"""
        if not self.redis:
            await self.connect()
        await self.redis.lpush(topic, json.dumps(message))
    
    async def publish_delayed(self, topic: str, message: dict, delay_sec: int) -> None:
        """
        发送延迟消息
        实际生产中建议用 Redis ZSET 实现，这里简化演示使用 asyncio.sleep
        """
        if not self.redis:
            await self.connect()
        
        async def _delayed_publish():
            await asyncio.sleep(delay_sec)
            await self.redis.lpush(topic, json.dumps(message))
        
        asyncio.create_task(_delayed_publish())
    
    async def consume(self, topic: str, handler: Callable) -> None:
        """消费指定主题的消息"""
        if not self.redis:
            await self.connect()
        
        while True:
            try:
                # 使用 BRPOP 阻塞式获取消息，超时1秒
                result = await self.redis.brpop(topic, timeout=1)
                if result:
                    _, data = result
                    msg = json.loads(data)
                    await handler(msg)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing message: {e}")
                # 短暂休眠后继续
                await asyncio.sleep(0.1)