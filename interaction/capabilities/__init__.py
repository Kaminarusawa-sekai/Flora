# 基础类和接口
from .base import (
    BaseManager,
    TaskStorage,
    MockTaskStorage
)
from .capability_base import CapabilityBase
from .capability_manager import CapabilityManager
from .registry import CapabilityRegistry

# 用户输入与意图识别
from .user_input_manager.interface import IUserInputManagerCapability
from .user_input_manager.common_user_input_manager import CommonUserInput
from .intent_recognition_manager.interface import IIntentRecognitionManagerCapability
from .intent_recognition_manager.common_intent_recognition_manager import CommonIntentRecognition

# 对话与任务管理
from .dialog_state_manager.interface import IDialogStateManagerCapability
from .dialog_state_manager.common_dialog_state_manager import CommonDialogState
from .task_draft_manager.interface import ITaskDraftManagerCapability
from .task_draft_manager.common_task_draft_manager import CommonTaskDraft
from .task_query_manager.interface import ITaskQueryManagerCapability
from .task_query_manager.common_task_query_manager import CommonTaskQuery
from .context_manager.interface import IContextManagerCapability
from .context_manager.common_context_manager import CommonContextManager

# 任务控制与执行
from .task_control_manager.interface import ITaskControlManagerCapability
from .task_control_manager.common_task_control_manager import CommonTaskControl
from .schedule_manager.interface import IScheduleManagerCapability
from .schedule_manager.common_schedule_manager import CommonSchedule
from .task_execution_manager.interface import ITaskExecutionManagerCapability
from .task_execution_manager.common_task_execution_manager import CommonTaskExecution
from .system_response_manager.interface import ISystemResponseManagerCapability
from .system_response_manager.common_system_response_manager import CommonSystemResponse

# 创建全局能力管理器实例
_global_manager = None
CONFIG_PATH = "./interaction/interaction_config.json"

# 导出常用接口
__all__ = [
    # 基础类和接口
    "BaseManager",
    "TaskStorage",
    "MockTaskStorage",
    "CapabilityBase",
    "CapabilityManager",
    "CapabilityRegistry",
    
    # 用户输入与意图识别
    "IUserInputManagerCapability",
    "CommonUserInput",
    "IIntentRecognitionManagerCapability",
    "CommonIntentRecognition",
    
    # 对话与任务管理
    "IDialogStateManagerCapability",
    "CommonDialogState",
    "ITaskDraftManagerCapability",
    "CommonTaskDraft",
    "ITaskQueryManagerCapability",
    "CommonTaskQuery",
    "IContextManagerCapability",
    "CommonContextManager",
    "IMemoryCapability",
    "Mem0MemoryCapability",
    
    # 任务控制与执行
    "ITaskControlManagerCapability",
    "CommonTaskControl",
    "IScheduleManagerCapability",
    "CommonSchedule",
    "ITaskExecutionManagerCapability",
    "CommonTaskExecution",
    "ISystemResponseManagerCapability",
    "CommonSystemResponse"
]

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