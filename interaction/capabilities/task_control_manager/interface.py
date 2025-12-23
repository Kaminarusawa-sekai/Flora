from typing import Dict, Any, Optional
from abc import abstractmethod
from ..base import BaseManager, TaskStorage
from common.task_execution import TaskExecutionContextDTO, TaskControlResponseDTO

class ITaskControlManagerCapability(BaseManager):
    """任务控制管理器接口"""
    
    def __init__(self, context: dict = None):
        super().__init__(context)
    
    @abstractmethod
    def cancel_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """取消任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def pause_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """暂停任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def resume_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """恢复任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def retry_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """重试任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def terminate_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """强制终止任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def pause_all_tasks(self, user_id: str) -> TaskControlResponseDTO:
        """暂停所有正在运行的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def handle_task_control(self, intent_result: Any, user_input: Any, user_id: str, dialog_state: Any, last_mentioned_task_id: Optional[str] = None) -> TaskControlResponseDTO:
        """处理任务控制意图
        
        Args:
            intent_result: 意图识别结果
            user_input: 原始用户输入
            user_id: 用户ID
            dialog_state: 对话状态上下文
            last_mentioned_task_id: 上次提到的任务ID
            
        Returns:
            操作结果
        """
        pass