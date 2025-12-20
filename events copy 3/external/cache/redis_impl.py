import redis.asyncio as redis
from typing import Optional, Any
from .base import CacheClient
from ...config.settings import settings


class RedisCacheClient(CacheClient):
    def __init__(self, redis_url: str = settings.redis_url):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        await self.redis.set(key, value, ex=ttl)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0


# 创建全局 redis 客户端实例
redis_client = RedisCacheClient()