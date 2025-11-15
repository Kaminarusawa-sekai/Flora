"""
任务协调模块
提供任务协调、管理和工作流控制功能
"""

# 导入任务协调器
from .task_coordinator import TaskCoordinator

# 导入任务状态相关定义（已迁移至routing模块）
from new.capabilities.routing.task_status import (
    TaskStatus,
    TaskDependency,
    TaskResult
)

# 导入任务规划器（已迁移至routing模块）
from new.capabilities.routing.task_planner import TaskPlanner

# 导入上下文解析器（已迁移至routing模块）
from new.capabilities.routing.context_resolver import ContextResolver

__all__ = [
    # 任务协调器
    'TaskCoordinator',
    
    # 任务状态相关定义
    'TaskStatus',
    'TaskDependency',
    'TaskResult',
    
    # 任务规划器
    'TaskPlanner',
    
    # 上下文解析器
    'ContextResolver'
]

__version__ = '1.0.0'
__author__ = 'Flora AI Team'
__description__ = '任务协调模块 - 提供任务生命周期管理和协调功能'
