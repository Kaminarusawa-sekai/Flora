import json
import time
from typing import Dict, Any, Optional, AsyncIterator
from .bus import EventBus
from ..cache.base import CacheClient

class RedisEventBus(EventBus):
    def __init__(self, cache_client: CacheClient):
        self.cache = cache_client
        self.consumer_group = "event_bus_group"
        self.consumer_name = f"consumer-{int(time.time())}"

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
    
    async def subscribe(self, topic: str) -> AsyncIterator[Dict[str, Any]]:
        """
        订阅 Redis Stream 事件
        :param topic: 对应 Redis Stream 的 Key
        :return: 事件迭代器
        """
        if not self.cache:
            return
        
        try:
            # 检查并创建消费者组
            try:
                await self.cache.xgroup_create(topic, self.consumer_group, mkstream=True)
            except Exception as e:
                # 消费者组已存在，忽略错误
                pass
            
            # 从最后一个事件开始消费
            last_id = "$"
            
            while True:
                # 阻塞等待新事件，超时时间 1 秒
                response = await self.cache.xreadgroup(
                    self.consumer_group, 
                    self.consumer_name, 
                    {topic: last_id}, 
                    count=1, 
                    block=1000
                )
                
                if response:
                    for stream in response:
                        stream_name, messages = stream
                        for message_id, message in messages:
                            last_id = message_id
                            # 解析消息
                            event_type = message.get("type", "")
                            key = message.get("key", "")
                            data = message.get("data", "{}")
                            
                            try:
                                payload = json.loads(data)
                            except json.JSONDecodeError:
                                payload = {}
                            
                            yield {
                                "key": key,
                                "event_type": event_type,
                                "payload": payload,
                                "message_id": message_id
                            }
        except Exception as e:
            # 记录日志: logger.error(f"Event bus subscribe failed: {e}")
            pass
