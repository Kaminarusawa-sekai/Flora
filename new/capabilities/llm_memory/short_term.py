"""短期记忆模块"""
from typing import Dict, Any, Optional, List
from collections import OrderedDict


class ShortTermMemory:
    """
    短期记忆管理类，存储临时的、短期使用的记忆数据
    使用有序字典实现LRU策略
    """
    
    def __init__(self, max_size: int = 1000):
        """
        初始化短期记忆
        
        Args:
            max_size: 最大存储项数，超过会自动清理最老的项
        """
        self.max_size = max_size
        self.memory = OrderedDict()
    
    def store(self, key: str, value: Any) -> bool:
        """
        存储记忆项
        
        Args:
            key: 键
            value: 值
            
        Returns:
            bool: 是否存储成功
        """
        try:
            # 如果已存在，先删除旧的
            if key in self.memory:
                del self.memory[key]
            
            # 检查是否超过最大容量
            if len(self.memory) >= self.max_size:
                # 删除最老的项（OrderedDict的第一个项）
                self.memory.popitem(last=False)
            
            # 添加新项到末尾
            self.memory[key] = value
            return True
        except Exception:
            return False
    
    def retrieve(self, key: str) -> Optional[Any]:
        """
        检索记忆项
        
        Args:
            key: 键
            
        Returns:
            检索到的值，如果不存在返回None
        """
        if key in self.memory:
            # 访问后将项移到末尾（表示最近使用）
            value = self.memory.pop(key)
            self.memory[key] = value
            return value
        return None
    
    def delete(self, key: str) -> bool:
        """
        删除记忆项
        
        Args:
            key: 键
            
        Returns:
            bool: 是否删除成功
        """
        if key in self.memory:
            del self.memory[key]
            return True
        return False
    
    def clear(self) -> bool:
        """
        清空所有记忆
        
        Returns:
            bool: 是否清空成功
        """
        try:
            self.memory.clear()
            return True
        except Exception:
            return False
    
    def get_all_keys(self) -> List[str]:
        """
        获取所有键
        
        Returns:
            List[str]: 键列表
        """
        return list(self.memory.keys())
    
    def get_size(self) -> int:
        """
        获取当前存储的项数
        
        Returns:
            int: 项数
        """
        return len(self.memory)
    
    def contains(self, key: str) -> bool:
        """
        检查是否包含指定的键
        
        Args:
            key: 键
            
        Returns:
            bool: 是否包含
        """
        return key in self.memory
