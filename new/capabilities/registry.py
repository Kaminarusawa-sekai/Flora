"""能力注册表"""
from typing import Dict, Any, Type, Optional
from .capability_base import CapabilityBase


class CapabilityRegistry:
    """
    能力注册表，负责管理和注册所有能力组件
    """
    
    _instance = None
    _capabilities = {}
    
    def __new__(cls):
        """
        单例模式实现
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, capability_type: str, capability_class: Type[CapabilityBase]) -> bool:
        """
        注册能力组件
        
        Args:
            capability_type: 能力类型标识符
            capability_class: 能力类
            
        Returns:
            bool: 是否注册成功
        """
        if not issubclass(capability_class, CapabilityBase):
            return False
        
        self._capabilities[capability_type] = capability_class
        return True
    
    def get_capability(self, capability_type: str) -> Optional[CapabilityBase]:
        """
        获取能力实例
        
        Args:
            capability_type: 能力类型标识符
            
        Returns:
            CapabilityBase: 能力实例，如果不存在返回None
        """
        if capability_type in self._capabilities:
            return self._capabilities[capability_type]()
        return None
    
    def get_all_capabilities(self) -> Dict[str, Type[CapabilityBase]]:
        """
        获取所有已注册的能力
        
        Returns:
            Dict[str, Type[CapabilityBase]]: 能力类型到类的映射
        """
        return self._capabilities.copy()
    
    def unregister(self, capability_type: str) -> bool:
        """
        取消注册能力组件
        
        Args:
            capability_type: 能力类型标识符
            
        Returns:
            bool: 是否取消成功
        """
        if capability_type in self._capabilities:
            del self._capabilities[capability_type]
            return True
        return False
    
    def has_capability(self, capability_type: str) -> bool:
        """
        检查是否有指定的能力
        
        Args:
            capability_type: 能力类型标识符
            
        Returns:
            bool: 是否存在
        """
        return capability_type in self._capabilities


# 创建全局注册表实例
capability_registry = CapabilityRegistry()
