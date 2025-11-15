"""
订阅者接口定义
为事件订阅者提供统一的接口规范
"""
from abc import ABC, abstractmethod
from typing import Dict, Any


class Subscriber(ABC):
    """订阅者抽象类，定义事件处理接口"""
    
    @abstractmethod
    def on_event(self, event: Dict[str, Any]) -> None:
        """
        处理接收到的事件
        
        Args:
            event: 事件字典，包含事件类型、源、数据、时间戳等信息
        """
        pass
