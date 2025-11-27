
from typing import Dict, Any, Callable, Optional, Protocol
from dataclasses import dataclass, asdict
from agent.optimization.optimization_task import OptimizationTask

# 定义持久化接口（Protocol，Python 3.8+）
class PersistenceAdapter(Protocol):
    def save_tasks(self, tasks: Dict[str, OptimizationTask]) -> None:
        """保存所有任务"""
        ...

    def load_tasks(self) -> Dict[str, OptimizationTask]:
        """加载所有任务"""
        ...


class EvaluatorAdapter(Protocol):
    """
    评估器接口：根据任务执行结果返回一个分数（越高越好）
    """
    def evaluate(self, task_id: str, result: Any) -> float:
        """
        :param task_id: 任务 ID
        :param result: 执行器返回的结果
        :return: 评分（建议 0.0 ~ 1.0，但不强制）
        """
        ...


class ImproverAdapter(Protocol):
    """
    优化器接口：根据评分调整系统行为（如更新参数、模型、配置等）
    """
    def improve(self, task_id: str, score: float) -> None:
        """
        :param task_id: 任务 ID
        :param score: 本次评估得分
        """
        ...