"""系统事件消息定义"""
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any


@dataclass
class SystemEventMessage:
    """
    系统事件消息类
    用于在系统各组件间传递标准化的事件信息，并作为数据库存储的映射对象
    """
    event_id: str
    trace_id: str             # 关键：用于追踪整个调用链 (Task ID)
    event_type: str
    source_component: str     # 哪个 Actor 发出的
    content: Dict[str, Any]   # 具体的事件数据 (参数、结果、错误堆栈)
    timestamp: float          # Unix timestamp
    level: str = "INFO"       # INFO, WARN, ERROR
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式，便于序列化和传输
        
        Returns:
            包含所有事件属性的字典
        """
        return {
            "event_id": self.event_id,
            "trace_id": self.trace_id,
            "event_type": self.event_type,
            "source_component": self.source_component,
            "content": self.content,
            "timestamp": self.timestamp,
            "level": self.level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SystemEventMessage':
        """
        从字典创建SystemEventMessage实例
        
        Args:
            data: 事件数据字典
            
        Returns:
            SystemEventMessage实例
        """
        return cls(
            event_id=data['event_id'],
            trace_id=data['trace_id'],
            event_type=data['event_type'],
            source_component=data['source_component'],
            content=data['content'],
            timestamp=data['timestamp'],
            level=data.get('level', 'INFO')
        )
    
    def to_db_dict(self) -> Dict[str, Any]:
        """
        转换为数据库存储格式
        
        Returns:
            适合数据库存储的字典
        """
        import json
        return {
            "id": self.event_id,
            "trace_id": self.trace_id,
            "event_type": self.event_type,
            "source": self.source_component,
            "content": json.dumps(self.content),
            "created_at": datetime.fromtimestamp(self.timestamp),
            "level": self.level
        }