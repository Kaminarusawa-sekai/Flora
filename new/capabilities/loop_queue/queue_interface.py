"""循环队列抽象接口"""
from abc import ABC, abstractmethod
from typing import Any, Callable, Optional


class LoopQueueInterface(ABC):
    """
    循环队列抽象接口，定义循环任务管理的标准操作
    """
    
    @abstractmethod
    def add_task(self, task: Callable, interval: int) -> str:
        """
        添加循环任务
        
        Args:
            task: 要执行的任务函数
            interval: 执行间隔（秒）
            
        Returns:
            str: 任务ID
        """
        pass
    
    @abstractmethod
    def remove_task(self, task_id: str) -> bool:
        """
        移除循环任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否移除成功
        """
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """
        启动循环队列
        
        Returns:
            bool: 是否启动成功
        """
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """
        停止循环队列
        
        Returns:
            bool: 是否停止成功
        """
        pass
    
    @abstractmethod
    def pause_task(self, task_id: str) -> bool:
        """
        暂停指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否暂停成功
        """
        pass
    
    @abstractmethod
    def resume_task(self, task_id: str) -> bool:
        """
        恢复指定任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否恢复成功
        """
        pass
    
    @abstractmethod
    def update_interval(self, task_id: str, new_interval: int) -> bool:
        """
        更新任务执行间隔
        
        Args:
            task_id: 任务ID
            new_interval: 新的执行间隔（秒）
            
        Returns:
            bool: 是否更新成功
        """
        pass
    
    @abstractmethod
    def get_task_status(self, task_id: str) -> Optional[dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            dict: 任务状态信息，如果任务不存在返回None
        """
        pass
