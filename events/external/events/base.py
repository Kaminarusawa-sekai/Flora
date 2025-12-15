from abc import ABC, abstractmethod
from typing import Dict, Any


class EventPublisher(ABC):
    """事件发布器抽象基类"""
    
    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]) -> None:
        """发布事件到指定主题"""
        pass
    
    @abstractmethod
    async def publish_delayed(self, topic: str, message: Dict[str, Any], delay_sec: int) -> None:
        """发布延时事件到指定主题"""
        pass