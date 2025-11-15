"""
并行执行模块
提供任务并行执行、调度和管理功能
"""

from .execution_manager import (
    ParallelExecutionManager
)

from .task_manager import (
    ParallelTaskManager,
    DynamicTaskScheduler,
    TaskInfo,
    create_parallel_task_manager,
    create_dynamic_task_scheduler
)

__all__ = [
    # 并行执行管理器
    'ParallelExecutionManager',
    
    # 并行任务管理器
    'ParallelTaskManager',
    'DynamicTaskScheduler',
    'TaskInfo',
    'create_parallel_task_manager',
    'create_dynamic_task_scheduler'
]

__version__ = '1.0.0'
__author__ = 'Flora AI Team'
__description__ = '并行执行模块 - 提供高效的并行任务处理能力'
