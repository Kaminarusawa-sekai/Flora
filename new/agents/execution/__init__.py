"""
任务执行模块
提供任务执行、策略管理和服务组件
"""



from .execution_strategy import (
    ExecutionStrategy,
    SequentialExecutionStrategy,
    ConditionalExecutionStrategy,
    MapReduceExecutionStrategy,
    ExecutionStrategyManager,
    get_strategy_manager
)

__all__ = [
    
    # 执行策略
    'ExecutionStrategy',
    'SequentialExecutionStrategy',

    'ConditionalExecutionStrategy',
    'MapReduceExecutionStrategy',
    'ExecutionStrategyManager',
    'get_strategy_manager'
]

__version__ = '1.0.0'
__author__ = 'Flora AI Team'
__description__ = '任务执行模块 - 提供灵活的任务执行机制和策略管理'
