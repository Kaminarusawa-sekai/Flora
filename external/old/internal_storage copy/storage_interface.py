"""内部存储抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class InternalStorageInterface(ABC):
    """
    内部持久化存储的抽象接口，定义数据持久化的标准方法
    """
    
    @abstractmethod
    def save_task_state(self, task_id: str, state_data: Dict[str, Any]) -> bool:
        """
        保存任务状态
        
        Args:
            task_id: 任务唯一标识符
            state_data: 任务状态数据
            
        Returns:
            是否保存成功
        """
        pass
    
    @abstractmethod
    def load_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        加载任务状态
        
        Args:
            task_id: 任务唯一标识符
            
        Returns:
            任务状态数据，如果不存在返回None
        """
        pass
    
    @abstractmethod
    def save_learning_model(self, model_id: str, model_data: Dict[str, Any]) -> bool:
        """
        保存自学习模型
        
        Args:
            model_id: 模型唯一标识符
            model_data: 模型数据
            
        Returns:
            是否保存成功
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭连接，释放资源
        """
        pass
    
    @abstractmethod
    def delete_task_state(self, task_id: str) -> bool:
        """
        删除任务状态
        
        Args:
            task_id: 任务唯一标识符
            
        Returns:
            是否删除成功
        """
        pass
