from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from common.types.task_operation import TaskOperationType, TaskOperationCategory
from capability_base import CapabilityBase


class ITaskOperationCapability(CapabilityBase):
    """任务操作分类能力接口"""

    @abstractmethod
    def initialize(self, config: Dict[str, Any] = None):
        """初始化能力"""
        return
    @abstractmethod
    def shutdown(self):
        """关闭能力"""
        return 
    @abstractmethod
    def is_available(self) -> bool:
        """检查能力是否可用"""
        return True
    @abstractmethod
    def get_capability_type(self) -> str:
        """获取能力类型"""
        return "task_operation"

    @abstractmethod
    def classify_operation(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分类任务操作

        Args:
            user_input: 用户输入
            context: 上下文信息（如历史任务、当前状态等）

        Returns:
            Dict包含:
                - operation_type: TaskOperationType
                - category: TaskOperationCategory
                - target_task_id: Optional[str] - 目标任务ID（如果适用）
                - parameters: Dict[str, Any] - 提取的参数
                - confidence: float - 置信度
        """
        raise NotImplementedError
