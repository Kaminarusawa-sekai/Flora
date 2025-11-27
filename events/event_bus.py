"""
事件总线实现
提供统一的事件发布和订阅管理机制
"""
from typing import Dict, Any, List, Optional, Callable, Union
from datetime import datetime
from threading import RLock

from .event_types import EventType
from .subscriber import Subscriber
from .publisher import Publisher
from ..common.messages.event_messages import EventMessage


class EventBus(Publisher):
    """
    事件总线实现
    提供事件的发布、订阅和管理功能
    采用单例模式确保系统中只有一个事件总线实例
    """
    
    _instance = None
    _lock = RLock()
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(EventBus, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化事件总线"""
        # 订阅者映射: event_type -> [subscribers]
        self._subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        # 全局订阅者（接收所有事件）
        self._global_subscribers: List[Callable[[Dict[str, Any]], None]] = []
        # 线程锁确保线程安全
        self._subscribers_lock = RLock()
        
    def subscribe(
        self, 
        event_types: Optional[List[EventType]] = None,
        handler: Optional[Callable[[Dict[str, Any]], None]] = None,
        subscriber: Optional[Subscriber] = None
    ) -> None:
        """
        订阅事件
        
        Args:
            event_types: 要订阅的事件类型列表
            handler: 事件处理函数
            subscriber: 订阅者对象（必须实现on_event方法）
            
        注意：必须提供handler或subscriber中的一个
        """
        # 验证参数
        if not handler and not subscriber:
            raise ValueError("必须提供handler或subscriber")
            
        # 确定事件处理函数
        event_handler = None
        if handler:
            event_handler = handler
        elif subscriber:
            event_handler = subscriber.on_event
        
        with self._subscribers_lock:
            if event_types is None or not event_types:
                # 订阅所有事件
                self._global_subscribers.append(event_handler)
            else:
                # 订阅特定事件类型
                for event_type in event_types:
                    event_type_value = event_type.value if isinstance(event_type, EventType) else event_type
                    if event_type_value not in self._subscribers:
                        self._subscribers[event_type_value] = []
                    self._subscribers[event_type_value].append(event_handler)
    
    def unsubscribe(
        self, 
        event_types: Optional[List[EventType]] = None,
        handler: Optional[Callable[[Dict[str, Any]], None]] = None,
        subscriber: Optional[Subscriber] = None
    ) -> None:
        """
        取消订阅事件
        
        Args:
            event_types: 要取消订阅的事件类型列表
            handler: 事件处理函数
            subscriber: 订阅者对象
            
        注意：必须提供handler或subscriber中的一个
        """
        # 验证参数
        if not handler and not subscriber:
            raise ValueError("必须提供handler或subscriber")
            
        # 确定事件处理函数
        event_handler = None
        if handler:
            event_handler = handler
        elif subscriber:
            event_handler = subscriber.on_event
        
        with self._subscribers_lock:
            if event_types is None or not event_types:
                # 取消订阅所有事件
                if event_handler in self._global_subscribers:
                    self._global_subscribers.remove(event_handler)
            else:
                # 取消订阅特定事件类型
                for event_type in event_types:
                    event_type_value = event_type.value if isinstance(event_type, EventType) else event_type
                    if event_type_value in self._subscribers:
                        if event_handler in self._subscribers[event_type_value]:
                            self._subscribers[event_type_value].remove(event_handler)
                            # 如果该事件类型没有订阅者了，移除该事件类型
                            if not self._subscribers[event_type_value]:
                                del self._subscribers[event_type_value]
    
    def publish_event(
        self, 
        event_type: Union[str, EventType], 
        source: str, 
        data: Optional[Dict[str, Any]] = None, 
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        发布事件
        
        Args:
            event_type: 事件类型 (字符串或EventType枚举)
            source: 事件源
            data: 事件数据
            timestamp: 事件时间戳
        """
        # 确保事件类型是EventType枚举
        if isinstance(event_type, str):
            # 从字符串转换为EventType枚举
            from .event_types import get_event_type
            event_type_enum = get_event_type(event_type)
            if event_type_enum is None:
                raise ValueError(f"Unknown event type: {event_type}")
        elif isinstance(event_type, EventType):
            event_type_enum = event_type
        else:
            raise TypeError(f"event_type must be a string or EventType Enum, got {type(event_type).__name__}")
        
        # 创建事件消息
        event = EventMessage(
            event_type=event_type_enum, 
            source=source, 
            data=data or {}, 
            timestamp=timestamp or datetime.now()
        )
        
        # 转换为字典格式
        event_dict = event.to_dict()
        
        # 分发事件
        self._dispatch_event(event_dict)
    
    def publish_task_event(
        self, 
        task_id: str, 
        event_type: str, 
        source: str, 
        agent_id: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发布任务相关事件
        
        Args:
            task_id: 任务ID
            event_type: 事件类型
            source: 事件源
            agent_id: 智能体ID
            data: 事件数据
        """
        # 创建任务事件数据
        task_data = data.copy() if data else {}
        task_data.update({
            'task_id': task_id,
            'agent_id': agent_id
        })
        
        # 发布事件
        self.publish_event(
            event_type=event_type, 
            source=source, 
            data=task_data
        )
    
    def publish_agent_event(
        self, 
        agent_id: str, 
        event_type: str, 
        source: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发布智能体相关事件
        
        Args:
            agent_id: 智能体ID
            event_type: 事件类型
            source: 事件源
            data: 事件数据
        """
        # 创建智能体事件数据
        agent_data = data.copy() if data else {}
        agent_data.update({
            'agent_id': agent_id
        })
        
        # 发布事件
        self.publish_event(
            event_type=event_type, 
            source=source, 
            data=agent_data
        )
    
    def _dispatch_event(self, event_dict: Dict[str, Any]) -> None:
        """
        分发事件给所有相关订阅者
        
        Args:
            event_dict: 事件字典
        """
        with self._subscribers_lock:
            # 获取事件类型
            event_type = event_dict['event_type']
            
            # 分发给全局订阅者
            for subscriber in self._global_subscribers:
                self._handle_event(subscriber, event_dict)
            
            # 分发给特定事件类型的订阅者
            if event_type in self._subscribers:
                for subscriber in self._subscribers[event_type]:
                    self._handle_event(subscriber, event_dict)
    
    def _handle_event(self, subscriber: Callable[[Dict[str, Any]], None], event: Dict[str, Any]) -> None:
        """
        处理单个事件
        
        Args:
            subscriber: 订阅者处理函数
            event: 事件字典
        """
        try:
            # 调用订阅者的事件处理函数
            subscriber(event)
        except Exception as e:
            # 捕获并记录订阅者处理事件时的异常
            import logging
            logger = logging.getLogger('event_bus')
            logger.error(f"订阅者处理事件时发生错误: {str(e)}", exc_info=True)
    
    def get_subscribers_count(self, event_type: Optional[EventType] = None) -> int:
        """
        获取订阅者数量
        
        Args:
            event_type: 事件类型
            
        Returns:
            订阅者数量
        """
        with self._subscribers_lock:
            if event_type is None:
                # 获取所有订阅者数量
                total = len(self._global_subscribers)
                for subscribers_list in self._subscribers.values():
                    total += len(subscribers_list)
                return total
            else:
                # 获取特定事件类型的订阅者数量
                event_type_value = event_type.value if isinstance(event_type, EventType) else event_type
                if event_type_value in self._subscribers:
                    return len(self._subscribers[event_type_value]) + len(self._global_subscribers)
                return len(self._global_subscribers)
    
    def clear(self) -> None:
        """
        清除所有订阅者
        """
        with self._subscribers_lock:
            self._subscribers.clear()
            self._global_subscribers.clear()


# 创建事件总线单例实例
event_bus = EventBus()
