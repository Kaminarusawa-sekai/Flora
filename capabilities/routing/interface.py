from abc import abstractmethod
from typing import Any
from ..capability_base import CapabilityBase


class ITaskRouter(CapabilityBase):
    """任务路由接口"""

    @abstractmethod
    def select_best_actor(self, task_description: str, context: Any) -> str:
        """分析任务并返回最佳执行者的标识符"""
        pass
    
    def get_capability_type(self) -> str:
        return "routing"