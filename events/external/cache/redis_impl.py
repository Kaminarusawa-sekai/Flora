import redis.asyncio as redis
from typing import Optional, Any
from .base import CacheClient
from config.settings import settings


class RedisCacheClient(CacheClient):
    def __init__(self, redis_url: str = settings.redis_url):
        self.redis = redis.from_url(redis_url, decode_responses=True)

    async def get(self, key: str) -> Optional[str]:
        return await self.redis.get(key)

    async def set(self, key: str, value: str, ttl: Optional[int] = None, **kwargs) -> None:
        # 如果 kwargs 中有 ex，则优先使用 ex，否则使用 ttl
        if 'ex' not in kwargs and ttl is not None:
            kwargs['ex'] = ttl
        await self.redis.set(key, value, **kwargs)

    async def delete(self, key: str) -> None:
        await self.redis.delete(key)

    async def exists(self, key: str) -> bool:
        return await self.redis.exists(key) > 0
    
    async def mget(self, keys: list[str]) -> list[Optional[str]]:
        return await self.redis.mget(keys)
    
    async def xadd(self, stream_key: str, data: dict, maxlen: Optional[int] = None) -> None:
        kwargs = {}
        if maxlen is not None:
            kwargs['maxlen'] = maxlen
            kwargs['approximate'] = True  # 使用近似截断，提高性能
        await self.redis.xadd(stream_key, data, **kwargs)


# 创建全局 redis 客户端实例
redis_client = RedisCacheClient()