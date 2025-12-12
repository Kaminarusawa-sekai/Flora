"""消息模块"""
from .event_message import SystemEventMessage
from .base_message import BaseMessage, TaskMessage
from .task_messages import (
    TaskCompletedMessage,
    MCPTaskRequestMessage,
    TaskGroupRequestMessage,
    ParallelTaskRequestMessage,
    ResultAggregatorTaskRequestMessage,
    ExecuteTaskMessage,
    ExecutionResultMessage
)
from .interact_messages import (
    UserRequestMessage,
    InitConfigMessage,
    TaskPausedMessage,
    TaskResultMessage
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
from .agent_messages import (
    AgentTaskMessage,
    ResumeTaskMessage
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
    
    # 代理相关消息
    "AgentTaskMessage",
    "ResumeTaskMessage",
    
    # 类型定义
    "MessageType"
]
