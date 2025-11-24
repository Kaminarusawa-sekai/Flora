"""
并行执行模块
提供任务并行执行、调度和管理功能
"""

from .execution_manager import (
    ParallelExecutionManager
)

__all__ = [
    # 并行执行管理器
    'ParallelExecutionManager'
]

__version__ = '1.0.0'
__author__ = 'Flora AI Team'
__description__ = '并行执行模块 - 提供高效的并行任务处理能力'
