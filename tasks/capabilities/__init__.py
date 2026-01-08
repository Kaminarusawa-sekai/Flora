"""能力模块统一入口"""
from .capability_manager import CapabilityManager
from .registry import CapabilityRegistry
from .capability_base import CapabilityBase

# 导出子模块
from . import context_resolver
from . import decision
from . import dimension
from . import draw_charts
from . import excution
from . import llm
from . import llm_memory
from . import multifeature
from . import optimization
from . import parallel
from . import result_aggregation
# from . import task_operation
from . import task_planning
from . import text_to_sql

# 导出常用接口
__all__ = [
    "CapabilityManager",
    "CapabilityRegistry",
    "CapabilityBase",
    "context_resolver",
    "decision",
    "dimension",
    "draw_charts",
    "excution",
    "llm",
    "llm_memory",
    "multifeature",
    "optimization",
    "parallel",
    "result_aggregation",
    "task_planning",
    "text_to_sql"
]

# 创建全局能力管理器实例
_global_manager = None
CONFIG_PATH = "./config.json"

def get_capability_manager(config_path: str = CONFIG_PATH) -> CapabilityManager:
    """
    获取全局能力管理器实例
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        能力管理器实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = CapabilityManager(config_path)
    return _global_manager


def init_capabilities(config_path: str = CONFIG_PATH) -> CapabilityManager:
    """
    初始化所有能力
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        能力管理器实例
    """
    manager = get_capability_manager(config_path)
    manager.auto_register_capabilities()
    manager.initialize_all_capabilities()
    return manager


def get_capability_registry() -> CapabilityRegistry:
    """
    获取能力注册表实例
    
    Returns:
        能力注册表实例
    """
    return CapabilityRegistry()


def get_capability(name: str, expected_type: type) -> CapabilityBase:
    """
    获取能力实例
    
    Args:
        name: 能力名称
        expected_type: 期望的能力类型
        
    Returns:
        能力实例
    """
    manager = get_capability_manager()
    return manager.get_capability(name, expected_type)