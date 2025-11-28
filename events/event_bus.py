"""
事件总线实现
简化为轻量级 SDK，方便系统中的任何地方快速发送事件给 EventActor
"""
from typing import Dict, Any, Optional
from thespian.actors import ActorSystem
from common.messages.event_message import SystemEventMessage
import time
import uuid
import logging


class EventBus:
    """
    事件总线实现
    简化为轻量级 SDK，方便系统中的任何地方快速发送事件给 EventActor
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
        # 初始化Actor系统
        self.system = ActorSystem()
        # 获取全局 EventActor 地址
        self.event_actor = self.system.createActor(
            'events.event_actor.EventActor',
            globalName='GlobalEventActor'
        )
        # 初始化日志
        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
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
        # 创建SystemEventMessage
        msg = SystemEventMessage(
            event_id=str(uuid.uuid4()),
            trace_id=trace_id,
            event_type=event_type,
            source_component=source,
            content=data,
            timestamp=time.time(),
            level=level
        )
        
        # Fire and Forget (不等待回执)
        try:
            self.system.tell(self.event_actor, msg)
            self.log.debug(f"Event published: {event_type}, trace_id: {trace_id}")
        except Exception as e:
            # 记录日志，但不要影响业务流程
            self.log.error(f"Failed to publish event: {str(e)}", exc_info=True)
    
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
        self.publish(
            trace_id=task_id,
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
