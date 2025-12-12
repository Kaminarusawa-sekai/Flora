"""能力注册表"""
import logging
from typing import Dict, Any, Type, Optional, Callable, TypeVar
from .capability_base import CapabilityBase

# T 是一个泛型，代表具体的 Capability 类型
T = TypeVar('T', bound='CapabilityBase')


class CapabilityRegistry:
    """
    能力注册表（支持依赖注入和泛型类型推断）
    """
    
    _instance = None
    _factories: Dict[str, Callable[[], CapabilityBase]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(
        self,
        capability_type: str,
        factory: Callable[[], CapabilityBase]
    ) -> bool:
        """
        注册能力工厂（推荐方式）
        
        Args:
            capability_type: 能力类型
            factory: 无参函数，返回已初始化的能力实例
        """
        self._factories[capability_type] = factory
        return True

    def register_class(
        self,
        capability_type: str,
        capability_class: Type[CapabilityBase],
        init_kwargs: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        辅助方法：通过类 + 初始化参数注册（适合简单场景）
        """
        def factory():
            instance = capability_class()
            if hasattr(instance, 'initialize'):
                instance.initialize(**(init_kwargs or {}))
            return instance
        
        return self.register(capability_type, factory)

    # 关键优化：使用泛型 T，让 IDE 知道返回的是什么具体的类
    def get_capability(self, name: str, expected_type: Type[T]) -> T:
        """
        获取指定类型的能力实例
        
        Args:
            name: 能力名称
            expected_type: 期望的能力类型
            
        Returns:
            符合期望类型的能力实例
            
        Raises:
            ValueError: 能力不存在
            TypeError: 能力类型不匹配
        """
        if name in self._factories:
            try:
                cap = self._factories[name]()
                if not isinstance(cap, expected_type):
                    raise TypeError(f"Capability {name} is not of type {expected_type.__name__}")
                return cap
            except Exception as e:
                logging.error(f"Failed to create capability '{name}': {e}")
                raise
        raise ValueError(f"Capability {name} not found")

    def has_capability(self, capability_type: str) -> bool:
        """
        检查是否有指定的能力
        
        Args:
            capability_type: 能力类型标识符
            
        Returns:
            bool: 是否存在
        """
        return capability_type in self._factories

    # 其他方法（unregister, get_all 等）可按需补充
    
    def get_all_capabilities(self) -> Dict[str, Callable[[], CapabilityBase]]:
        """
        获取所有已注册的能力
        
        Returns:
            Dict[str, Callable[[], CapabilityBase]]: 能力类型到工厂函数的映射
        """
        return self._factories.copy()
    
    def unregister(self, capability_type: str) -> bool:
        """
        取消注册能力组件
        
        Args:
            capability_type: 能力类型标识符
            
        Returns:
            bool: 是否取消成功
        """
        if capability_type in self._factories:
            del self._factories[capability_type]
            return True
        return False

##TODO:单例模式，到时候全局统一管理
# 创建全局注册表实例
capability_registry = CapabilityRegistry()
