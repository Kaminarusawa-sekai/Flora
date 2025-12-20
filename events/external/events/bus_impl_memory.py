from typing import Dict, Any, Optional
from .bus import EventBus

class MemoryEventBus(EventBus):
    """
    内存事件总线实现，用于本地调试和单元测试
    """
    
    def __init__(self):
        self.events = []
    
    async def publish(self, topic: str, event_type: str, key: str, payload: Dict[str, Any]) -> bool:
        """
        在内存中记录事件，不实际发送
        :param topic: 主题
        :param event_type: 事件类型
        :param key: 业务键
        :param payload: 消息体
        :return: 是否发送成功
        """
        event = {
            "topic": topic,
            "event_type": event_type,
            "key": key,
            "payload": payload
        }
        self.events.append(event)
        print(f"[MockBus] Published to {topic}: {event_type} - {payload}")
        return True
    
    def get_events(self, clear: bool = True) -> list:
        """
        获取所有事件并可选择清除
        :param clear: 是否清除事件列表
        :return: 事件列表
        """
        events = self.events.copy()
        if clear:
            self.events.clear()
        return events
