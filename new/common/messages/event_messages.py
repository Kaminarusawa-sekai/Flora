"""事件消息定义"""
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime


class EventType(Enum):
    """事件类型枚举"""
    # 系统事件
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    SYSTEM_ERROR = "system_error"
    
    # 任务事件
    TASK_CREATED = "task_created"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_PROGRESS = "task_progress"
    
    # 数据事件
    DATA_UPDATED = "data_updated"
    DATA_CREATED = "data_created"
    DATA_DELETED = "data_deleted"
    
    # 优化事件
    OPTIMIZATION_STARTED = "optimization_started"
    OPTIMIZATION_COMPLETED = "optimization_completed"
    PARAMETER_UPDATED = "parameter_updated"
    
    # 资源事件
    RESOURCE_ALLOCATED = "resource_allocated"
    RESOURCE_RELEASED = "resource_released"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    
    # 安全事件
    SECURITY_AUTHENTICATION = "security_authentication"
    SECURITY_AUTHORIZATION = "security_authorization"
    SECURITY_BREACH = "security_breach"


class EventMessage:
    """
    事件消息基类
    用于在系统各组件间传递标准化的事件信息
    """
    
    def __init__(
        self,
        event_type: EventType,
        source: str,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        初始化事件消息
        
        Args:
            event_type: 事件类型
            source: 事件源（组件名称或ID）
            data: 事件相关数据
            timestamp: 事件时间戳
            priority: 事件优先级（0-10，默认0）
            metadata: 附加元数据
        """
        self.event_type = event_type
        self.source = source
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()
        self.priority = max(0, min(10, priority))  # 确保优先级在0-10范围内
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，便于序列化和传输
        
        Returns:
            包含所有事件属性的字典
        """
        return {
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp,
            "priority": self.priority,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EventMessage':
        """
        从字典创建EventMessage实例
        
        Args:
            data: 事件数据字典
            
        Returns:
            EventMessage实例
        """
        timestamp = data.get('timestamp')
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            event_type=EventType(data['event_type']),
            source=data['source'],
            data=data.get('data', {}),
            timestamp=timestamp,
            priority=data.get('priority', 0),
            metadata=data.get('metadata', {})
        )
    
    def is_error(self) -> bool:
        """
        判断是否为错误事件
        
        Returns:
            是否为错误事件
        """
        return self.event_type in [
            EventType.SYSTEM_ERROR,
            EventType.TASK_FAILED,
            EventType.RESOURCE_EXHAUSTED,
            EventType.SECURITY_BREACH
        ]
    
    def is_high_priority(self) -> bool:
        """
        判断是否为高优先级事件
        
        Returns:
            是否为高优先级事件（优先级>=7）
        """
        return self.priority >= 7
    
    def __str__(self) -> str:
        """
        字符串表示
        
        Returns:
            事件的可读字符串表示
        """
        return f"EventMessage(type={self.event_type.value}, source={self.source}, priority={self.priority})"


class EventBatch:
    """
    事件批次，用于批量处理和传输多个事件
    """
    
    def __init__(self):
        """初始化事件批次"""
        self.events: list[EventMessage] = []
    
    def add_event(self, event: EventMessage) -> None:
        """
        添加事件到批次
        
        Args:
            event: 要添加的事件
        """
        self.events.append(event)
    
    def add_multiple(self, events: list[EventMessage]) -> None:
        """
        批量添加事件
        
        Args:
            events: 事件列表
        """
        self.events.extend(events)
    
    def get_events_by_type(self, event_type: EventType) -> list[EventMessage]:
        """
        根据类型获取事件
        
        Args:
            event_type: 要筛选的事件类型
            
        Returns:
            符合条件的事件列表
        """
        return [e for e in self.events if e.event_type == event_type]
    
    def get_high_priority_events(self) -> list[EventMessage]:
        """
        获取所有高优先级事件
        
        Returns:
            高优先级事件列表
        """
        return [e for e in self.events if e.is_high_priority()]
    
    def get_error_events(self) -> list[EventMessage]:
        """
        获取所有错误事件
        
        Returns:
            错误事件列表
        """
        return [e for e in self.events if e.is_error()]
    
    def to_dict_list(self) -> list[Dict[str, Any]]:
        """
        转换为字典列表
        
        Returns:
            所有事件的字典表示列表
        """
        return [event.to_dict() for event in self.events]
    
    @property
    def size(self) -> int:
        """
        获取批次大小
        
        Returns:
            事件数量
        """
        return len(self.events)
    
    def clear(self) -> None:
        """
        清空批次中的所有事件
        """
        self.events.clear()
