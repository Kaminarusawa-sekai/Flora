from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from ..capability_base import CapabilityBase


class IMemoryCapability(CapabilityBase):
    """
    记忆服务接口：负责存取，不关心底层是 Mem0 还是向量数据库
    """
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        pass

    @abstractmethod
    def shutdown(self) -> None:
        pass

    @abstractmethod
    def get_capability_type(self) -> str:
        """
        返回能力类型，如 'llm', 'memory', 'data_access'
        """
        return "memory"

    @abstractmethod
    def search_memories(self, user_id: str, query: str, limit: int = 5) -> str:
        """检索相关记忆，返回拼接好的文本"""
        pass

    @abstractmethod
    def add_memory(self, user_id: str, text: str) -> None:
        """添加一条交互记录或事实"""
        pass

    # 可选扩展：核心记忆管理（允许用户调整）
    def list_core_memories(self, user_id: str, limit: int = 50):
        """列出用户核心记忆"""
        raise NotImplementedError

    def set_core_memory(self, user_id: str, key: str, value: str) -> None:
        """设置/更新用户核心记忆"""
        raise NotImplementedError

    def delete_core_memory(self, user_id: str, key: str) -> None:
        """删除用户核心记忆"""
        raise NotImplementedError
