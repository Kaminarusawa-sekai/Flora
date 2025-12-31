from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, AsyncIterator

class EventBus(ABC):
    """
    事件总线抽象基类
    """
    
    @abstractmethod
    async def publish(self, topic: str, event_type: str, key: str, payload: Dict[str, Any]) -> bool:
        """
        发布事件
        :param topic: 主题 (对应 Redis Key 或 Kafka Topic)
        :param event_type: 事件类型 (如 TRACE_CREATED)
        :param key: 业务键 (如 trace_id，用于 Kafka 分区或日志索引)
        :param payload: 消息体
        :return: 是否发送成功
        """
        pass
    
    @abstractmethod
    async def subscribe(self, topic: str) -> AsyncIterator[Dict[str, Any]]:
        """
        订阅事件
        :param topic: 主题 (对应 Redis Key 或 Kafka Topic)
        :return: 事件迭代器
        """
        pass
