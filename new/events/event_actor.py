"""事件报告Actor"""
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime
from thespian.actors import Actor
from ..common.messages.event_messages import EventMessage, EventType
from .event_bus import event_bus
from .event_types import EventType as NewEventType


class EventActor(Actor):
    """
    事件报告Actor，负责处理和分发系统中的各种事件
    基于原Observer/observer_actor.py重构
    """
    
    def __init__(self, tenant_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """初始化事件报告Actor"""
        self.subscribers = {}  # subscriber_id -> subscriber_info
        self.event_history = []
        self.max_history_size = 1000
        # 初始化事件总线
        self.event_bus = event_bus
        # 初始化日志
        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def receiveMessage(self, message: Any, sender: Actor) -> None:
        """
        接收并处理消息
        
        Args:
            message: 接收到的消息
            sender: 发送者Actor
        """
        if isinstance(message, dict):
            message_type = message.get('type')
            
            if message_type == 'register_subscriber':
                self._register_subscriber(message, sender)
            elif message_type == 'unregister_subscriber':
                self._unregister_subscriber(message)
            elif message_type == 'publish_event':
                self._publish_event(message)
            elif message_type == 'get_event_history':
                self._get_event_history(message, sender)
            elif message_type == 'subscribe_to_event':
                self._subscribe_to_event(message, sender)
            elif message_type == 'unsubscribe_from_event':
                self._unsubscribe_from_event(message)
    
    def _register_subscriber(self, message: Dict[str, Any], sender: Actor) -> None:
        """
        注册事件订阅者
        
        Args:
            message: 包含订阅者信息的消息
            sender: 发送者Actor
        """
        subscriber_id = message.get('subscriber_id', str(sender))
        event_types = message.get('event_types', [])
        
        self.subscribers[subscriber_id] = {
            'actor': sender,
            'event_types': event_types
        }
        
        self.send(sender, {'status': 'success', 'message': 'Subscribed successfully'})
    
    def _unregister_subscriber(self, message: Dict[str, Any]) -> None:
        """
        注销事件订阅者
        
        Args:
            message: 包含订阅者ID的消息
        """
        subscriber_id = message.get('subscriber_id')
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
    
    def _publish_event(self, message: Dict[str, Any]) -> None:
        """
        发布事件
        
        Args:
            message: 包含事件信息的消息
        """
        event_type = message.get('event_type')
        source = message.get('source')
        data = message.get('data')
        timestamp = message.get('timestamp')
        
        # 确保event_type是EventType枚举
        try:
            if isinstance(event_type, str):
                event_type_enum = EventType(event_type.upper())
            elif isinstance(event_type, EventType):
                event_type_enum = event_type
            else:
                self.log.error(f"Invalid event_type type: {type(event_type)}")
                return
        except ValueError:
            self.log.error(f"Invalid event_type: {event_type}")
            return
        
        # 创建事件消息
        event = EventMessage(
            event_type=event_type_enum,
            source=source,
            data=data,
            timestamp=timestamp
        )
        
        # 存储事件历史
        self._store_event(event)
        
        # 通过事件总线分发事件
        self.event_bus.publish_event(
            event_type=event_type_enum,
            source=source,
            data=data,
            timestamp=timestamp
        )
        
        # 同时保持原有的本地分发展机制
        self._distribute_event(event)
    
    def _store_event(self, event: EventMessage) -> None:
        """
        存储事件到历史记录
        
        Args:
            event: 事件消息
        """
        self.event_history.append(event.to_dict())
        # 限制历史记录大小
        if len(self.event_history) > self.max_history_size:
            self.event_history = self.event_history[-self.max_history_size:]
    
    def store_event(self, event_type: str, data: Dict[str, Any]):
        """
        存储事件（从请求处理程序调用）
        
        Args:
            event_type: 事件类型（字符串）
            data: 事件数据
        """
        try:
            # 转换事件类型为EventType枚举
            event_type_enum = EventType(event_type.upper())
        except ValueError:
            # 如果无法转换，记录错误并返回
            self.log.error(f"Invalid event_type: {event_type}")
            return
        
        # 创建事件消息
        event = EventMessage(
            event_type=event_type_enum,
            source="request_handler",
            data=data,
            timestamp=data.get('timestamp', datetime.now().isoformat())
        )
        
        # 存储事件
        self._store_event(event)
        
        # 通过事件总线发布事件
        try:
            self.event_bus.publish_event(
                event_type=event_type_enum,
                source="request_handler",
                data=data,
                timestamp=event.timestamp
            )
        except Exception as e:
            self.log.error(f"Failed to publish event: {str(e)}")
    
    def _distribute_event(self, event: EventMessage) -> None:
        """
        分发事件给相关订阅者
        
        Args:
            event: 事件对象
        """
        for subscriber_id, subscriber in self.subscribers.items():
            # 如果订阅了所有事件或特定事件类型
            if not subscriber['event_types'] or event.event_type in subscriber['event_types']:
                self.send(subscriber['actor'], event.to_dict())
    
    def _get_event_history(self, message: Dict[str, Any], sender: Actor) -> None:
        """
        获取事件历史
        
        Args:
            message: 查询消息
            sender: 发送者Actor
        """
        event_type = message.get('event_type')
        limit = message.get('limit', 100)
        
        filtered_history = self.event_history
        if event_type:
            filtered_history = [e for e in filtered_history if e['event_type'] == event_type]
        
        # 返回最新的事件
        result = filtered_history[-limit:]
        self.send(sender, {'status': 'success', 'events': result})
    
    def _subscribe_to_event(self, message: Dict[str, Any], sender: Actor) -> None:
        """
        订阅特定事件类型
        
        Args:
            message: 订阅消息
            sender: 发送者Actor
        """
        event_types = message.get('event_types', [])
        subscriber_id = message.get('subscriber_id', str(sender))
        
        if subscriber_id not in self.subscribers:
            self.subscribers[subscriber_id] = {
                'actor': sender,
                'event_types': []
            }
        
        # 添加新的事件类型
        for event_type in event_types:
            if event_type not in self.subscribers[subscriber_id]['event_types']:
                self.subscribers[subscriber_id]['event_types'].append(event_type)
    
    def _unsubscribe_from_event(self, message: Dict[str, Any]) -> None:
        """
        取消订阅特定事件类型
        
        Args:
            message: 取消订阅消息
        """
        event_types = message.get('event_types', [])
        subscriber_id = message.get('subscriber_id')
        
        if subscriber_id in self.subscribers:
            for event_type in event_types:
                if event_type in self.subscribers[subscriber_id]['event_types']:
                    self.subscribers[subscriber_id]['event_types'].remove(event_type)
