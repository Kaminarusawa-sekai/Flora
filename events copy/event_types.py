"""
事件类型定义模块
整合系统所有事件类型，提供统一的事件类型管理
"""
from enum import Enum
from typing import Dict, Any, Optional


class EventType(str, Enum):
    """事件类型枚举，包含所有系统事件类型"""
    # 基础系统事件
    SYSTEM_STARTUP = "SYSTEM_STARTUP"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    SYSTEM_ERROR = "SYSTEM_ERROR"
    
    # 任务生命周期 (对应 Timeline 展示)
    TASK_CREATED = "TASK_CREATED"
    TASK_PLANNING = "TASK_PLANNING"       # 新增：规划中
    TASK_DISPATCHED = "TASK_DISPATCHED"   # 新增：分发给子Agent
    TASK_RUNNING = "TASK_RUNNING"
    TASK_COMPLETED = "TASK_COMPLETED"
    TASK_FAILED = "TASK_FAILED"
    TASK_PROGRESS = "TASK_PROGRESS"
    TASK_CANCELLED = "TASK_CANCELLED"
    TASK_RESUMED = "TASK_RESUMED"
    TASK_PAUSED = "TASK_PAUSED"
    TASK_QUEUED = "TASK_QUEUED"
    
    # 子任务事件
    SUBTASK_SPAWNED = "SUBTASK_SPAWNED"
    SUBTASK_COMPLETED = "SUBTASK_COMPLETED"
    
    # 调试/监控
    AGENT_THINKING = "AGENT_THINKING"     # 记录 Agent 的思考过程 (CoT)
    TOOL_CALLED = "TOOL_CALLED"           # 记录工具调用输入
    TOOL_RESULT = "TOOL_RESULT"           # 记录工具调用输出
    
    # 智能体相关事件
    AGENT_CREATED = "AGENT_CREATED"
    AGENT_DESTROYED = "AGENT_DESTROYED"
    AGENT_UPDATED = "AGENT_UPDATED"
    AGENT_IDLE = "AGENT_IDLE"
    AGENT_BUSY = "AGENT_BUSY"
    
    # 基础数据事件
    DATA_UPDATED = "DATA_UPDATED"
    DATA_CREATED = "DATA_CREATED"
    DATA_DELETED = "DATA_DELETED"
    DATA_QUERY_EXECUTED = "DATA_QUERY_EXECUTED"
    DATA_QUERY_FAILED = "DATA_QUERY_FAILED"
    DATA_EXPORTED = "DATA_EXPORTED"
    
    # 基础优化事件
    OPTIMIZATION_STARTED = "OPTIMIZATION_STARTED"
    OPTIMIZATION_COMPLETED = "OPTIMIZATION_COMPLETED"
    PARAMETER_UPDATED = "PARAMETER_UPDATED"

    # 详细优化事件
    OPTIMIZATION_REGISTERED = "OPTIMIZATION_REGISTERED"       # 注册优化
    OPTIMIZATION_UNREGISTERED = "OPTIMIZATION_UNREGISTERED"   # 取消注册
    OPTIMIZATION_LEARNED = "OPTIMIZATION_LEARNED"             # 学习反馈
    OPTIMIZATION_TRIGGERED = "OPTIMIZATION_TRIGGERED"         # 触发优化
    OPTIMIZATION_RESET = "OPTIMIZATION_RESET"                 # 重置优化器
    OPTIMIZATION_APPLIED = "OPTIMIZATION_APPLIED"             # 应用优化结果

    # 循环任务事件
    LOOP_TASK_REGISTERED = "LOOP_TASK_REGISTERED"            # 循环任务注册
    LOOP_TASK_TRIGGERED = "LOOP_TASK_TRIGGERED"              # 循环任务触发
    TASK_TRIGGERED = "TASK_TRIGGERED"                        # 任务触发（通用）
    TASK_UPDATED = "TASK_UPDATED"                            # 任务更新
    
    # 基础资源事件
    RESOURCE_ALLOCATED = "RESOURCE_ALLOCATED"
    RESOURCE_RELEASED = "RESOURCE_RELEASED"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    
    # 能力相关事件
    CAPABILITY_EXECUTED = "CAPABILITY_EXECUTED"
    CAPABILITY_FAILED = "CAPABILITY_FAILED"
    CAPABILITY_ERROR = "CAPABILITY_ERROR"
    CAPABILITY_REGISTERED = "CAPABILITY_REGISTERED"
    
    # 并行执行相关事件
    PARALLEL_EXECUTION_STARTED = "PARALLEL_EXECUTION_STARTED"
    PARALLEL_EXECUTION_COMPLETED = "PARALLEL_EXECUTION_COMPLETED"
    
    # 评论相关事件
    COMMENT_ADDED = "COMMENT_ADDED"


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
    return event_type.value.startswith('TASK_') or event_type.value.startswith('SUBTASK_')


def is_agent_event(event_type: EventType) -> bool:
    """
    判断事件类型是否为智能体相关事件
    
    Args:
        event_type: 事件类型
        
    Returns:
        True如果是智能体相关事件，否则False
    """
    return event_type.value.startswith('AGENT_')


def is_data_event(event_type: EventType) -> bool:
    """
    判断事件类型是否为数据相关事件
    
    Args:
        event_type: 事件类型
        
    Returns:
        True如果是数据相关事件，否则False
    """
    return event_type.value.startswith('DATA_')


def is_debug_event(event_type: EventType) -> bool:
    """
    判断事件类型是否为调试相关事件
    
    Args:
        event_type: 事件类型
        
    Returns:
        True如果是调试相关事件，否则False
    """
    debug_events = [
        EventType.AGENT_THINKING,
        EventType.TOOL_CALLED,
        EventType.TOOL_RESULT
    ]
    return event_type in debug_events
