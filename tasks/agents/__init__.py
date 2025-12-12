"""
Flora 智能体系统 - 代理层（agents）

此模块提供智能体的核心功能，包括智能体执行、任务处理、并行执行和协调等能力。
"""

__version__ = "1.0.0"
__author__ = "Flora Team"

# 导入子模块
from . import agent_actor
from . import tree
from . import actor_reference_utils
from .agent_actor import AgentActor
from .leaf_actor import LeafActor
from .router_actor import RouterActor, UserRequest

# 导出主要组件
__all__ = [
    # 模块导出
    "agent_actor",
    "tree",
    "actor_reference_utils",
    
    # 类导出
    "AgentActor",
    "LeafActor",
    "RouterActor",
    "UserRequest",
]

