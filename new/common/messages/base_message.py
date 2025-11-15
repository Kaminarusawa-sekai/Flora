"""消息基类模块"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime
from ..utils import to_json, from_json


class BaseMessage(ABC):
    """
    所有消息的基类
    定义了消息的基本结构和行为
    """
    
    def __init__(self, message_type: str, source: str, destination: str, timestamp: Optional[datetime] = None):
        """
        初始化消息
        
        Args:
            message_type: 消息类型
            source: 消息源（发送者）
            destination: 消息目的地（接收者）
            timestamp: 消息时间戳
        """
        self.message_type = message_type
        self.source = source
        self.destination = destination
        self.timestamp = timestamp or datetime.now()
        self._id = self._generate_id()  # 消息唯一ID
    
    @abstractmethod
    def _generate_id(self) -> str:
        """
        生成消息唯一ID
        
        Returns:
            消息ID
        """
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            消息字典
        """
        return {
            "id": self._id,
            "message_type": self.message_type,
            "source": self.source,
            "destination": self.destination,
            "timestamp": self.timestamp.isoformat() if hasattr(self.timestamp, 'isoformat') else str(self.timestamp)
        }
    
    def to_json(self) -> str:
        """
        转换为JSON字符串
        
        Returns:
            JSON字符串
        """
        return to_json(self.to_dict())
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseMessage':
        """
        从字典创建消息实例
        
        Args:
            data: 消息字典
            
        Returns:
            消息实例
        """
        message = cls.__new__(cls)  # 创建实例但不调用__init__
        message._id = data.get('id', '')
        message.message_type = data.get('message_type', '')
        message.source = data.get('source', '')
        message.destination = data.get('destination', '')
        message.timestamp = datetime.fromisoformat(data.get('timestamp', ''))
        return message
    
    @classmethod
    def from_json(cls, json_str: str) -> 'BaseMessage':
        """
        从JSON字符串创建消息实例
        
        Args:
            json_str: JSON字符串
            
        Returns:
            消息实例
        """
        data = from_json(json_str)
        return cls.from_dict(data)
    
    def __str__(self) -> str:
        """
        字符串表示
        """
        return f"{self.__class__.__name__}[{self._id}] {self.message_type} from {self.source} to {self.destination} at {self.timestamp}"
    
    def __repr__(self) -> str:
        """
        详细表示
        """
        return f"{self.__class__.__name__}(id={self._id}, type={self.message_type}, source={self.source}, dest={self.destination}, ts={self.timestamp})"


class SimpleMessage(BaseMessage):
    """
    简单消息实现
    用于传输基本的文本或数据
    """
    
    def __init__(self, source: str, destination: str, content: Any, message_type: str = "simple", timestamp: Optional[datetime] = None):
        """
        初始化简单消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            content: 消息内容
            message_type: 消息类型
            timestamp: 时间戳
        """
        super().__init__(message_type, source, destination, timestamp)
        self.content = content
    
    def _generate_id(self) -> str:
        """
        生成消息ID
        """
        import uuid
        return str(uuid.uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "content": self.content
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimpleMessage':
        """
        从字典创建简单消息
        """
        message = super().from_dict(data)
        message.content = data.get('content', '')
        return message