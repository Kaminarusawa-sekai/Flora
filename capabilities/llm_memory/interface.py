from abc import abstractmethod
from typing import Any, Dict
from ..capability_base import CapabilityBase


class IMemoryCapability(CapabilityBase):
    """记忆能力的外部调用接口"""

    @abstractmethod
    def add_memory_intelligently(self, content: Any, metadata: Dict = None) -> None:
        """智能路由并存储记忆"""
        pass

    @abstractmethod
    def build_conversation_context(self, user_id: str, window_size: int = 10) -> str:
        """构建对话上下文"""
        pass
    
    @abstractmethod
    def retrieve_relevant_memory(self, query: str) -> str:
        """检索相关记忆（语义+情景等）"""
        pass

    def get_capability_type(self) -> str:
        return "memory"