"""能力基类定义"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class CapabilityBase(ABC):
    """
    所有能力组件的基类，提供通用接口和生命周期管理
    """
    
    def __init__(self):
        """
        初始化能力组件
        """
        self.name = self.get_capability_name()
        self.is_initialized = False
    
    def initialize(self) -> bool:
        """
        初始化能力组件
        
        Returns:
            bool: 初始化是否成功
        """
        self.is_initialized = True
        return True
    
    def get_capability_name(self) -> str:
        """
        获取能力名称
        
        Returns:
            str: 能力名称
        """
        return self.__class__.__name__
    
    @abstractmethod
    def get_capability_type(self) -> str:
        """
        获取能力类型
        
        Returns:
            str: 能力类型标识符
        """
        pass
    
    def shutdown(self) -> None:
        """
        关闭能力组件，释放资源
        """
        self.is_initialized = False
    
    def get_status(self) -> Dict[str, Any]:
        """
        获取能力组件状态
        
        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            'name': self.name,
            'type': self.get_capability_type(),
            'initialized': self.is_initialized
        }
