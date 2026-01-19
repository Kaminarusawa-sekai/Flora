from abc import ABC, abstractmethod
from typing import Dict, Any


class MessageBroker(ABC):
    @abstractmethod
    async def publish(self, topic: str, message: Dict[str, Any]) -> None: ...
    @abstractmethod
    async def publish_delayed(self, topic: str, message: Dict[str, Any], delay_sec: int) -> None: ...
    @abstractmethod
    async def consume(self, topic: str, handler: callable) -> None: ...