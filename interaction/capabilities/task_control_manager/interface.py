from typing import Dict, Any
from abc import abstractmethod
from ..base import BaseManager, TaskStorage
from ...common import TaskExecutionContextDTO

class ITaskControlManager(BaseManager):
    """任务控制管理器接口"""
    
    def __init__(self, task_storage: TaskStorage, task_execution_manager: Any, context: dict = None):
        super().__init__(context)
        self.task_storage = task_storage
        self.task_execution_manager = task_execution_manager
    
    @abstractmethod
    def cancel_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """取消任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def pause_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """暂停任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def resume_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """恢复任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def retry_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """重试任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def terminate_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """强制终止任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass
    
    @abstractmethod
    def pause_all_tasks(self, user_id: str) -> Dict[str, Any]:
        """暂停所有正在运行的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        pass