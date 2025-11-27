"""优化方法抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class OptimizationInterface(ABC):
    """
    优化方法抽象接口，定义通用自优化接口
    所有优化方法实现都应遵循此接口
    """
    
    @abstractmethod
    def optimize_task(self, task: Dict[str, Any], history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        优化任务执行
        
        Args:
            task: 任务信息字典
            history_data: 历史执行数据列表
            
        Returns:
            Dict[str, Any]: 优化后的任务参数
        """
        pass
    
    @abstractmethod
    def learn_from_result(self, task_id: str, result: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> bool:
        """
        从执行结果中学习
        
        Args:
            task_id: 任务ID
            result: 执行结果
            feedback: 可选的反馈信息
            
        Returns:
            bool: 是否学习成功
        """
        pass
    
    @abstractmethod
    def get_best_parameters(self) -> Optional[Dict[str, Any]]:
        """
        获取当前的最佳参数
        
        Returns:
            Dict[str, Any]: 最佳参数配置，如果没有可用参数返回None
        """
        pass
    
    @abstractmethod
    def reset(self) -> bool:
        """
        重置优化器状态
        
        Returns:
            bool: 是否重置成功
        """
        pass
    
    @abstractmethod
    def save_state(self) -> Dict[str, Any]:
        """
        保存优化器状态
        
        Returns:
            Dict[str, Any]: 优化器状态数据
        """
        pass
    
    @abstractmethod
    def load_state(self, state_data: Dict[str, Any]) -> bool:
        """
        加载优化器状态
        
        Args:
            state_data: 优化器状态数据
            
        Returns:
            bool: 是否加载成功
        """
        pass
    
    @abstractmethod
    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        获取优化统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        pass
