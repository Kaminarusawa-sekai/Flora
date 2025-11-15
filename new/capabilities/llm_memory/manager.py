"""统一记忆管理器"""
from typing import Dict, Any, List, Optional
from ..capability_base import CapabilityBase
from .short_term import ShortTermMemory
from .resource_memory import ResourceMemory


class UnifiedMemoryManager:
    """
    统一记忆管理器，负责管理短期记忆和资源记忆
    """
    
    def __init__(self):
        """
        初始化统一记忆管理器
        """
        self.short_term = ShortTermMemory()
        self.resource_memory = ResourceMemory()
    
    def store_item(self, key: str, value: Any, memory_type: str = 'short_term') -> bool:
        """
        存储记忆项
        
        Args:
            key: 键
            value: 值
            memory_type: 记忆类型 ('short_term' 或 'resource')
            
        Returns:
            bool: 是否存储成功
        """
        if memory_type == 'short_term':
            return self.short_term.store(key, value)
        elif memory_type == 'resource':
            return self.resource_memory.store(key, value)
        return False
    
    def retrieve_item(self, key: str, memory_type: str = 'short_term') -> Optional[Any]:
        """
        检索记忆项
        
        Args:
            key: 键
            memory_type: 记忆类型 ('short_term' 或 'resource')
            
        Returns:
            检索到的值，如果不存在返回None
        """
        if memory_type == 'short_term':
            return self.short_term.retrieve(key)
        elif memory_type == 'resource':
            return self.resource_memory.retrieve(key)
        return None
    
    def delete_item(self, key: str, memory_type: str = 'short_term') -> bool:
        """
        删除记忆项
        
        Args:
            key: 键
            memory_type: 记忆类型 ('short_term' 或 'resource')
            
        Returns:
            bool: 是否删除成功
        """
        if memory_type == 'short_term':
            return self.short_term.delete(key)
        elif memory_type == 'resource':
            return self.resource_memory.delete(key)
        return False
    
    def clear(self, memory_type: Optional[str] = None) -> bool:
        """
        清空记忆
        
        Args:
            memory_type: 记忆类型，如果为None则清空所有记忆
            
        Returns:
            bool: 是否清空成功
        """
        if memory_type is None:
            return self.short_term.clear() and self.resource_memory.clear()
        elif memory_type == 'short_term':
            return self.short_term.clear()
        elif memory_type == 'resource':
            return self.resource_memory.clear()
        return False


class MemoryCapability(CapabilityBase):
    """
    记忆能力组件
    """
    
    def __init__(self):
        """
        初始化记忆能力
        """
        super().__init__()
        self.manager = None
    
    def initialize(self) -> bool:
        """
        初始化记忆组件
        """
        if not super().initialize():
            return False
        
        self.manager = UnifiedMemoryManager()
        return True
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'memory'
    
    def store(self, key: str, value: Any, memory_type: str = 'short_term') -> bool:
        """
        存储记忆
        """
        if not self.manager:
            return False
        return self.manager.store_item(key, value, memory_type)
    
    def retrieve(self, key: str, memory_type: str = 'short_term') -> Optional[Any]:
        """
        检索记忆
        """
        if not self.manager:
            return None
        return self.manager.retrieve_item(key, memory_type)
    
    def delete(self, key: str, memory_type: str = 'short_term') -> bool:
        """
        删除记忆
        """
        if not self.manager:
            return False
        return self.manager.delete_item(key, memory_type)
    
    def shutdown(self) -> None:
        """
        关闭记忆能力，释放资源
        """
        super().shutdown()
        if self.manager:
            self.manager.clear()
            self.manager = None
