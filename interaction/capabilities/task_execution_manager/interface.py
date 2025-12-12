from typing import Dict, Any, Optional, List
from abc import abstractmethod
from ..base import BaseManager, TaskStorage
from ...common import (
    TaskExecutionContextDTO,
    ExecutionStatus,
    ExecutionLogEntry
)

class ITaskExecutionManager(BaseManager):
    """任务执行管理器接口"""
    
    def __init__(self, task_storage: TaskStorage, context: Dict[str, Any] = None):
        super().__init__(context)
        self.task_storage = task_storage
        self.running_tasks: Dict[str, Any] = {}  # 存储正在运行的任务实例
    
    @abstractmethod
    def execute_task(self, draft_id: str, parameters: Dict[str, Any], task_type: str, user_id: str) -> TaskExecutionContextDTO:
        """执行任务
        
        Args:
            draft_id: 关联的草稿ID
            parameters: 执行参数
            task_type: 任务类型
            user_id: 用户ID
            
        Returns:
            任务执行上下文DTO
        """
        pass
    
    @abstractmethod
    def stop_task(self, task_id: str):
        """停止任务执行
        
        Args:
            task_id: 任务ID
        """
        pass
    
    @abstractmethod
    def pause_task(self, task_id: str):
        """暂停任务执行
        
        Args:
            task_id: 任务ID
        """
        pass
    
    @abstractmethod
    def resume_task(self, task_id: str):
        """恢复任务执行
        
        Args:
            task_id: 任务ID
        """
        pass
    
    @abstractmethod
    def retry_task(self, task_id: str):
        """重试任务执行
        
        Args:
            task_id: 任务ID
        """
        pass
    
    @abstractmethod
    def terminate_task(self, task_id: str):
        """强制终止任务执行
        
        Args:
            task_id: 任务ID
        """
        pass
    
    @abstractmethod
    def handle_task_interruption(self, task_id: str, field_name: str, message: str):
        """处理任务中断，等待用户输入
        
        Args:
            task_id: 任务ID
            field_name: 等待输入的字段名
            message: 中断消息
        """
        pass
    
    @abstractmethod
    def resume_interrupted_task(self, task_id: str, input_value: Any):
        """恢复被中断的任务
        
        Args:
            task_id: 任务ID
            input_value: 用户输入的值
        """
        pass
    
    @abstractmethod
    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """完成任务
        
        Args:
            task_id: 任务ID
            result: 任务执行结果
        """
        pass
    
    @abstractmethod
    def fail_task(self, task_id: str, error: Dict[str, Any]):
        """标记任务失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        pass