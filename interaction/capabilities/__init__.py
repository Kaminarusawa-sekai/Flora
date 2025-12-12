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
from .user_input_manager.interface import IUserInputManager
from .user_input_manager.common_implementation import CommonUserInputManager
from .intent_recognition_manager.interface import IIntentRecognitionManager
from .intent_recognition_manager.common_implementation import CommonIntentRecognitionManager

# 对话与任务管理
from .dialog_state_manager.interface import IDialogStateManager
from .dialog_state_manager.common_implementation import CommonDialogStateManager
from .task_draft_manager.interface import ITaskDraftManager
from .task_draft_manager.common_implementation import CommonTaskDraftManager
from .task_query_manager.interface import ITaskQueryManager
from .task_query_manager.common_implementation import CommonTaskQueryManager

# 任务控制与执行
from .task_control_manager.interface import ITaskControlManager
from .task_control_manager.common_implementation import CommonTaskControlManager
from .schedule_manager.interface import IScheduleManager
from .schedule_manager.common_implementation import CommonScheduleManager
from .task_execution_manager.interface import ITaskExecutionManager
from .task_execution_manager.common_implementation import CommonTaskExecutionManager
from .system_response_manager.interface import ISystemResponseManager
from .system_response_manager.common_implementation import CommonSystemResponseManager

__all__ = [
    # 基础类和接口
    "BaseManager",
    "TaskStorage",
    "MockTaskStorage",
    "CapabilityBase",
    "CapabilityManager",
    "CapabilityRegistry",
    
    # 用户输入与意图识别
    "IUserInputManager",
    "CommonUserInputManager",
    "IIntentRecognitionManager",
    "CommonIntentRecognitionManager",
    
    # 对话与任务管理
    "IDialogStateManager",
    "CommonDialogStateManager",
    "ITaskDraftManager",
    "CommonTaskDraftManager",
    "ITaskQueryManager",
    "CommonTaskQueryManager",
    
    # 任务控制与执行
    "ITaskControlManager",
    "CommonTaskControlManager",
    "IScheduleManager",
    "CommonScheduleManager",
    "ITaskExecutionManager",
    "CommonTaskExecutionManager",
    "ISystemResponseManager",
    "CommonSystemResponseManager"
]