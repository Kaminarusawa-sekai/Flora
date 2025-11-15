"""资源记忆模块"""
from typing import Dict, Any, Optional, List
import json
import os
from datetime import datetime


class ResourceMemory:
    """
    资源记忆管理类，存储长期的、结构化的资源信息
    支持持久化存储
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化资源记忆
        
        Args:
            storage_path: 持久化存储路径，如果为None则只保存在内存中
        """
        self.memory = {}
        self.storage_path = storage_path
        self._load_from_storage()
    
    def store(self, key: str, value: Any) -> bool:
        """
        存储资源项
        
        Args:
            key: 键
            value: 值，需要是可JSON序列化的
            
        Returns:
            bool: 是否存储成功
        """
        try:
            # 确保值可以序列化
            json.dumps(value)
            
            # 添加时间戳信息
            resource_item = {
                'value': value,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            self.memory[key] = resource_item
            self._save_to_storage()
            return True
        except Exception:
            return False
    
    def retrieve(self, key: str) -> Optional[Any]:
        """
        检索资源项
        
        Args:
            key: 键
            
        Returns:
            检索到的值，如果不存在返回None
        """
        if key in self.memory:
            return self.memory[key]['value']
        return None
    
    def delete(self, key: str) -> bool:
        """
        删除资源项
        
        Args:
            key: 键
            
        Returns:
            bool: 是否删除成功
        """
        if key in self.memory:
            del self.memory[key]
            self._save_to_storage()
            return True
        return False
    
    def clear(self) -> bool:
        """
        清空所有资源记忆
        
        Returns:
            bool: 是否清空成功
        """
        try:
            self.memory.clear()
            if self.storage_path:
                open(self.storage_path, 'w').close()  # 清空文件
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
    
    def get_resource_info(self, key: str) -> Optional[Dict[str, Any]]:
        """
        获取资源的完整信息（包括元数据）
        
        Args:
            key: 键
            
        Returns:
            Dict[str, Any]: 包含值和元数据的字典
        """
        return self.memory.get(key)
    
    def _save_to_storage(self) -> None:
        """
        将内存中的数据保存到存储路径
        """
        if self.storage_path:
            try:
                # 确保目录存在
                os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
                # 保存数据
                with open(self.storage_path, 'w', encoding='utf-8') as f:
                    json.dump(self.memory, f, ensure_ascii=False, indent=2)
            except Exception:
                # 保存失败不抛出异常，只记录到日志
                pass
    
    def _load_from_storage(self) -> None:
        """
        从存储路径加载数据到内存
        """
        if self.storage_path and os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    self.memory = json.load(f)
            except Exception:
                # 加载失败，使用空字典
                self.memory = {}
