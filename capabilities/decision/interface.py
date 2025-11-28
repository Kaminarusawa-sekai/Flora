from abc import abstractmethod
from typing import Dict, Any
from ..capability_base import CapabilityBase


class ITaskStrategyCapability(CapabilityBase):
    """任务策略判断能力接口"""
    
    @abstractmethod
    def decide_task_strategy(self, task_desc: str, context: str) -> Dict[str, Any]:
        """
        使用LLM判断任务策略：
        - 是否为循环任务（如每日报告）
        - 是否应并行执行（如生成多个创意方案）

        返回 dict 包含:
          is_loop: bool
          is_parallel: bool
          reasoning: str (LLM 的思考过程)
        """
        pass


class ITaskOperationCapability(CapabilityBase):
    """任务操作分类能力接口"""
    
    @abstractmethod
    def classify_task_operation(self, user_input: str, intent: Any = None) -> str:
        """
        使用LLM判断具体的任务操作
        
        Returns:
            操作类型: "LOOP_TASK" | "NEW_TASK" | 具体操作类型
        """
        pass