from typing import Dict, Any, Optional, AsyncIterator
from .bus import EventBus

class MemoryEventBus(EventBus):
    """
    内存事件总线实现，用于本地调试和单元测试
    """
    
    def __init__(self):
        self.events = []
        self.subscribers = []
    
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
    
    async def subscribe(self, topic: str) -> AsyncIterator[Dict[str, Any]]:
        """
        订阅内存事件
        :param topic: 主题
        :return: 事件迭代器
        """
        # 简单实现，返回所有事件
        for event in self.events:
            if event["topic"] == topic:
                yield {
                    "key": event["key"],
                    "event_type": event["event_type"],
                    "payload": event["payload"]
                }
        
        # 无限循环，模拟阻塞等待
        while True:
            # 检查是否有新事件
            for event in self.events:
                if event["topic"] == topic:
                    yield {
                        "key": event["key"],
                        "event_type": event["event_type"],
                        "payload": event["payload"]
                    }
            # 短暂睡眠，避免占用过多CPU
            import asyncio
            await asyncio.sleep(0.1)
    
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
