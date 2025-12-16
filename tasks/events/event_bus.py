"""
事件总线实现
简化为轻量级 SDK，方便系统中的任何地方快速发送事件
"""
from typing import Dict, Any, Optional
from common.event import Event, EventType, get_event_type
import logging


class EventBus:
    """
    事件总线实现
    简化为轻量级 SDK，方便系统中的任何地方快速发送事件
    采用单例模式确保系统中只有一个事件总线实例
    """
    
    _instance = None
    
    def __new__(cls):
        """实现单例模式"""
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """初始化事件总线"""
        # 初始化日志
        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.log.info("EventBus initialized successfully")
    
    def publish(
        self, 
        trace_id: str, 
        event_type: str, 
        source: str, 
        data: Dict[str, Any], 
        level: str = "INFO"
    ) -> None:
        """
        全系统通用的埋点方法
        
        Args:
            trace_id: 用于追踪整个调用链 (Task ID)
            event_type: 事件类型
            source: 事件源
            data: 事件数据
            level: 日志级别
        """
        try:
            # 转换为EventType枚举
            event_type_enum = get_event_type(event_type)
            if not event_type_enum:
                self.log.warning(f"Unknown event type: {event_type}, using SYSTEM_ERROR instead")
                event_type_enum = EventType.SYSTEM_ERROR
            
            # 从data中提取task_id和task_path，如果没有则使用默认值
            task_id = data.get('task_id', trace_id)  # 优先使用data中的task_id
            task_path = data.get('task_path', source)  # 优先使用data中的task_path，否则使用source
            
            # 创建Event对象
            event = Event(
                event_type=event_type_enum,
                trace_id=trace_id,
                task_id=task_id,
                task_path=task_path,
                payload={
                    **data,
                    "source": source,
                    "level": level
                }
            )
            
            # 简化实现：只记录日志，后续再实现真实发布逻辑
            self.log.info(f"Event published: {event_type}, trace_id: {trace_id}, event: {event.model_dump()}")
        except Exception as e:
            # 记录日志，但不要影响业务流程
            self.log.error(f"Failed to publish event: {str(e)}", exc_info=True)
    
    def publish_task_event(
        self, 
        task_id: str, 
        event_type: str, 
        trace_id: str, 
        task_path: str,
        source: str, 
        agent_id: str, 
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        message_type: Optional[str] = None,
        enriched_context_snapshot: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> Event:
        """
        发布任务相关事件，直接构建并返回Event对象
        
        Args:
            task_id: 任务ID
            event_type: 事件类型
            trace_id: 用于追踪整个调用链
            task_path: 任务路径
            source: 事件源
            agent_id: 智能体ID
            data: 事件数据
            user_id: 用户ID（可选）
            message_type: 消息类型（可选）
            enriched_context_snapshot: 快照关键上下文（可选）
            error: 错误信息（可选）
        
        Returns:
            构建好的Event对象
        """
        try:
            # 转换为EventType枚举
            event_type_enum = get_event_type(event_type)
            if not event_type_enum:
                self.log.warning(f"Unknown event type: {event_type}, using SYSTEM_ERROR instead")
                event_type_enum = EventType.SYSTEM_ERROR
            
            # 创建Event对象
            event = Event(
                event_type=event_type_enum,
                trace_id=trace_id,
                task_id=task_id,
                task_path=task_path,
                user_id=user_id,
                message_type=message_type,
                payload={
                    **(data or {}),
                    "source": source,
                    "agent_id": agent_id
                },
                enriched_context_snapshot=enriched_context_snapshot,
                error=error
            )
            
            # 简化实现：只记录日志，后续再实现真实发布逻辑
            self.log.info(f"Event published: {event_type}, trace_id: {trace_id}, task_id: {task_id}")
            self.log.info(f"Event details: {event.model_dump()}")
            
            return event
        except Exception as e:
            self.log.error(f"Failed to publish task event: {str(e)}", exc_info=True)
            raise
    
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
        self.publish(
            trace_id=f"agent_{agent_id}",
            event_type=event_type,
            source=source,
            data=agent_data
        )
    
    def publish_tool_event(
        self, 
        trace_id: str, 
        tool_name: str, 
        params: Dict[str, Any], 
        result: Optional[Any] = None
    ) -> None:
        """
        发布工具调用事件
        
        Args:
            trace_id: 追踪ID
            tool_name: 工具名称
            params: 工具调用参数
            result: 工具调用结果
        """
        # 发布工具调用事件
        self.publish(
            trace_id=trace_id,
            event_type="TOOL_CALLED",
            source="tool_caller",
            data={
                "tool_name": tool_name,
                "params": params
            }
        )
        
        # 如果有结果，发布工具结果事件
        if result is not None:
            self.publish(
                trace_id=trace_id,
                event_type="TOOL_RESULT",
                source="tool_caller",
                data={
                    "tool_name": tool_name,
                    "result": result
                }
            )
    
    def publish_agent_thinking(
        self, 
        trace_id: str, 
        agent_id: str, 
        thought: str
    ) -> None:
        """
        发布Agent思考过程事件
        
        Args:
            trace_id: 追踪ID
            agent_id: Agent ID
            thought: 思考内容
        """
        self.publish(
            trace_id=trace_id,
            event_type="AGENT_THINKING",
            source=agent_id,
            data={
                "agent_id": agent_id,
                "thought": thought
            }
        )


# 创建事件总线单例实例
event_bus = EventBus()
