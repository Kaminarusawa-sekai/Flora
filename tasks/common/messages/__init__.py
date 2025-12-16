"""消息模块"""
from .base_message import BaseMessage
from .event_message import SystemEventMessage
from .task_messages import (
    TaskMessage,
    TaskCompletedMessage,
    MCPTaskRequestMessage,
    TaskGroupRequestMessage,
    ParallelTaskRequestMessage,
    ResultAggregatorTaskRequestMessage,
    ExecuteTaskMessage,
    ExecutionResultMessage,
    AgentTaskMessage,
    ResumeTaskMessage
)

from .optimization_messages import (
    OptimizationMessage,
    OptimizationStartedMessage,
    OptimizationCompletedMessage,
    OptimizationFailedMessage,
    ParameterUpdatedMessage,
    OptimizationProgressMessage,
    OptimizationConvergedMessage
)
from .types import MessageType

__all__ = [
    # 基础消息类
    "BaseMessage",
    "TaskMessage",
    "SystemEventMessage",
    
    # 任务相关消息
    "TaskCompletedMessage",
    "MCPTaskRequestMessage",
    "TaskGroupRequestMessage",
    "ParallelTaskRequestMessage",
    "ResultAggregatorTaskRequestMessage",
    "ExecuteTaskMessage",
    "ExecutionResultMessage",
    
    # 代理相关消息
    "AgentTaskMessage",
    "ResumeTaskMessage",
    
    # 交互相关消息
    "UserRequestMessage",
    "InitConfigMessage",
    "TaskPausedMessage",
    "TaskResultMessage",
    
    # 优化相关消息
    "OptimizationMessage",
    "OptimizationStartedMessage",
    "OptimizationCompletedMessage",
    "OptimizationFailedMessage",
    "ParameterUpdatedMessage",
    "OptimizationProgressMessage",
    "OptimizationConvergedMessage",
    
    # 类型定义
    "MessageType"
]
