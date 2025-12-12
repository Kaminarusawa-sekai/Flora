"""能力基类定义"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TypeVar, Generic

# T 是一个泛型，代表具体的 Capability 类型
T = TypeVar('T', bound='CapabilityBase')


class CapabilityBase(ABC):
    """
    所有能力的基类，只负责生命周期和基础元数据
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
        pass

    def get_status(self) -> dict:
        return {"status": "ok"}
    
