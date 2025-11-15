"""
任务执行模块
提供任务执行、策略管理和服务组件
"""

from .task_execution_service import (
    TaskExecutionService
)

from .execution_strategy import (
    ExecutionStrategy,
    SequentialExecutionStrategy,
    ParallelExecutionStrategy,
    ConditionalExecutionStrategy,
    MapReduceExecutionStrategy,
    ExecutionStrategyManager,
    get_strategy_manager
)

__all__ = [
    # 任务执行服务
    'TaskExecutionService',
    
    # 执行策略
    'ExecutionStrategy',
    'SequentialExecutionStrategy',
    'ParallelExecutionStrategy',
    'ConditionalExecutionStrategy',
    'MapReduceExecutionStrategy',
    'ExecutionStrategyManager',
    'get_strategy_manager'
]

__version__ = '1.0.0'
__author__ = 'Flora AI Team'
__description__ = '任务执行模块 - 提供灵活的任务执行机制和策略管理'
