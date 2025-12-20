import json
import time
from typing import Dict, Any, Optional
from .bus import EventBus
from ..cache.base import CacheClient

class RedisEventBus(EventBus):
    def __init__(self, cache_client: CacheClient):
        self.cache = cache_client

    async def publish(self, topic: str, event_type: str, key: str, payload: Dict[str, Any]) -> bool:
        """
        使用 Redis Stream 发布事件
        :param topic: 对应 Redis Stream 的 Key
        :param event_type: 事件类型
        :param key: 业务键
        :param payload: 消息体
        :return: 是否发送成功
        """
        if not self.cache:
            return False

        event_data = {
            "type": event_type,
            "key": key,
            "ts": int(time.time() * 1000),  # 毫秒级时间戳
            "data": json.dumps(payload)  # 序列化消息体
        }
        
        try:
            # 使用 Redis Stream 发送事件，限制流的长度为 100000
            await self.cache.xadd(topic, event_data, maxlen=100000)
            return True
        except Exception as e:
            # 记录日志: logger.error(f"Event bus publish failed: {e}")
            return False
