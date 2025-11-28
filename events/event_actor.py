"""事件报告Actor"""
from typing import Dict, Any, Optional
import logging
import uuid
from thespian.actors import Actor
from common.messages.event_message import SystemEventMessage


class EventActor(Actor):
    """
    事件报告Actor，负责将事件消息持久化到数据库
    核心变革：EventActor 不再是事件的终点，而是事件的“搬运工”，
    它负责将瞬时消息搬运到持久化存储（Database）中
    """
    
    def __init__(self, tenant_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """初始化事件报告Actor"""
        # 初始化日志
        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # 初始化事件仓库 (用于持久化存储)
        from external.repositories.event_repo import EventRepository
        self.event_repo = EventRepository()
    
    def _create_mock_repository(self):
        """
        创建模拟事件仓库实例
        
        Returns:
            模拟事件仓库实例
        """
        class MockEventRepository:
            def __init__(self):
                self.events = []
                # 初始化日志
                self.log = logging.getLogger(f"{__name__}.MockEventRepository")
            
            def save(self, event: SystemEventMessage):
                """模拟保存事件"""
                self.events.append(event.to_dict())
                self.log.info(f"Mock saving event: {event.event_id}, type: {event.event_type}")
                return True
            
            def get_timeline(self, trace_id: str):
                """模拟获取时间轴"""
                # 过滤出符合trace_id的事件，并按时间排序
                filtered_events = [e for e in self.events if e["trace_id"] == trace_id]
                filtered_events.sort(key=lambda x: x["timestamp"])
                return filtered_events
        
        return MockEventRepository()
    
    def receiveMessage(self, message: Any, sender: Actor) -> None:
        """
        接收并处理消息
        
        Args:
            message: 接收到的消息
            sender: 发送者Actor
        """
        # 处理SystemEventMessage
        if isinstance(message, SystemEventMessage):
            self._persist_event(message)
        
        # 兼容旧格式的事件消息
        elif isinstance(message, dict):
            message_type = message.get('type')
            
            if message_type == 'publish_event':
                self._handle_legacy_event(message)
            elif message_type == 'store_event':
                self._handle_store_event(message)
    
    def _persist_event(self, event: SystemEventMessage) -> None:
        """
        持久化事件到数据库
        
        Args:
            event: 系统事件消息
        """
        try:
            # 调用事件仓库保存事件
            self.event_repo.save(event)
            self.log.debug(f"Event persisted successfully: {event.event_id}, type: {event.event_type}")
        except Exception as e:
            # 记录日志，但不要让EventActor崩溃
            self.log.error(f"Failed to save event: {str(e)}", exc_info=True)
    
    def _handle_legacy_event(self, message: Dict[str, Any]) -> None:
        """
        处理旧格式的事件消息
        
        Args:
            message: 旧格式的事件消息
        """
        import time
        
        event_type = message.get('event_type')
        source = message.get('source')
        data = message.get('data', {})
        timestamp = message.get('timestamp', time.time())
        
        # 从数据中提取trace_id，如果没有则使用默认值
        trace_id = data.get('task_id', f"default_{uuid.uuid4()}")
        
        # 转换为SystemEventMessage
        system_event = SystemEventMessage(
            event_id=str(uuid.uuid4()),
            trace_id=trace_id,
            event_type=event_type,
            source_component=source,
            content=data,
            timestamp=timestamp,
            level="INFO"
        )
        
        # 持久化事件
        self._persist_event(system_event)
    
    def _handle_store_event(self, message: Dict[str, Any]) -> None:
        """
        处理store_event消息
        
        Args:
            message: store_event消息
        """
        import time
        
        event_type = message.get('event_type')
        data = message.get('data', {})
        
        # 从数据中提取trace_id，如果没有则使用默认值
        trace_id = data.get('task_id', f"default_{uuid.uuid4()}")
        
        # 转换为SystemEventMessage
        system_event = SystemEventMessage(
            event_id=str(uuid.uuid4()),
            trace_id=trace_id,
            event_type=event_type,
            source_component="request_handler",
            content=data,
            timestamp=time.time(),
            level="INFO"
        )
        
        # 持久化事件
        self._persist_event(system_event)
    
    def store_event(self, event_type: str, data: Dict[str, Any]):
        """
        存储事件（从请求处理程序调用）
        
        Args:
            event_type: 事件类型（字符串）
            data: 事件数据
        """
        import time
        
        # 从数据中提取trace_id，如果没有则使用默认值
        trace_id = data.get('task_id', f"default_{uuid.uuid4()}")
        
        # 转换为SystemEventMessage
        system_event = SystemEventMessage(
            event_id=str(uuid.uuid4()),
            trace_id=trace_id,
            event_type=event_type,
            source_component="request_handler",
            content=data,
            timestamp=time.time(),
            level="INFO"
        )
        
        # 持久化事件
        self._persist_event(system_event)
