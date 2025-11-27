"""
事件类型定义模块
整合系统所有事件类型，提供统一的事件类型管理
"""
from enum import Enum
from typing import Dict, Any, Optional

from ..common.messages.event_messages import EventType as BaseEventType


class EventType(Enum):
    """事件类型枚举，包含所有系统事件类型"""
    # 基础系统事件
    SYSTEM_STARTUP = BaseEventType.SYSTEM_STARTUP.value
    SYSTEM_SHUTDOWN = BaseEventType.SYSTEM_SHUTDOWN.value
    SYSTEM_ERROR = BaseEventType.SYSTEM_ERROR.value
    
    # 基础任务事件
    TASK_CREATED = BaseEventType.TASK_CREATED.value
    TASK_COMPLETED = BaseEventType.TASK_COMPLETED.value
    TASK_FAILED = BaseEventType.TASK_FAILED.value
    TASK_PROGRESS = BaseEventType.TASK_PROGRESS.value
    
    # 基础数据事件
    DATA_UPDATED = BaseEventType.DATA_UPDATED.value
    DATA_CREATED = BaseEventType.DATA_CREATED.value
    DATA_DELETED = BaseEventType.DATA_DELETED.value
    
    # 基础优化事件
    OPTIMIZATION_STARTED = BaseEventType.OPTIMIZATION_STARTED.value
    OPTIMIZATION_COMPLETED = BaseEventType.OPTIMIZATION_COMPLETED.value
    PARAMETER_UPDATED = BaseEventType.PARAMETER_UPDATED.value
    
    # 基础资源事件
    RESOURCE_ALLOCATED = BaseEventType.RESOURCE_ALLOCATED.value
    RESOURCE_RELEASED = BaseEventType.RESOURCE_RELEASED.value
    RESOURCE_EXHAUSTED = BaseEventType.RESOURCE_EXHAUSTED.value
    
    # 扩展任务事件
    TASK_STARTED = "task_started"
    TASK_CANCELLED = "task_cancelled"
    TASK_RESUMED = "task_resumed"
    TASK_PAUSED = "task_paused"
    TASK_QUEUED = "task_queued"
    SUBTASK_SPAWNED = "subtask_spawned"
    
    # 智能体相关事件
    AGENT_CREATED = "agent_created"
    AGENT_DESTROYED = "agent_destroyed"
    AGENT_UPDATED = "agent_updated"
    AGENT_IDLE = "agent_idle"
    AGENT_BUSY = "agent_busy"
    
    # 数据扩展事件
    DATA_QUERY_EXECUTED = "data_query_executed"
    DATA_QUERY_FAILED = "data_query_failed"
    DATA_EXPORTED = "data_exported"
    
    # 能力相关事件
    CAPABILITY_EXECUTED = "capability_executed"
    CAPABILITY_FAILED = "capability_failed"
    CAPABILITY_REGISTERED = "capability_registered"
    
    # 并行执行相关事件
    PARALLEL_EXECUTION_STARTED = "parallel_execution_started"
    PARALLEL_EXECUTION_COMPLETED = "parallel_execution_completed"
    SUBTASK_COMPLETED = "subtask_completed"
    
    # 评论相关事件
    COMMENT_ADDED = "comment_added"


def get_event_type(value: str) -> Optional[EventType]:
    """
    根据字符串值获取EventType枚举
    
    Args:
        value: 事件类型字符串
        
    Returns:
        EventType枚举或None
    """
    try:
        return EventType(value)
    except ValueError:
        return None


def is_task_event(event_type: EventType) -> bool:
    """
    判断事件类型是否为任务相关事件
    
    Args:
        event_type: 事件类型
        
    Returns:
        True如果是任务相关事件，否则False
    """
    return event_type.value.startswith('task_') or event_type.value.startswith('subtask_')


def is_agent_event(event_type: EventType) -> bool:
    """
    判断事件类型是否为智能体相关事件
    
    Args:
        event_type: 事件类型
        
    Returns:
        True如果是智能体相关事件，否则False
    """
    return event_type.value.startswith('agent_')


def is_data_event(event_type: EventType) -> bool:
    """
    判断事件类型是否为数据相关事件
    
    Args:
        event_type: 事件类型
        
    Returns:
        True如果是数据相关事件，否则False
    """
    return event_type.value.startswith('data_')
