# optimization/schemas.py
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
from enum import Enum

class OptimizationDirection(str, Enum):
    maximize = "maximize"
    minimize = "minimize"

class SamplerType(str, Enum):
    tpe = "tpe"
    cmaes = "cmaes"
    random = "random"

class ParameterDefinition(BaseModel):
    """定义一个参数的搜索空间"""
    type: str  # "float", "int", "categorical"
    low: Optional[float] = None
    high: Optional[float] = None
    choices: Optional[List[Any]] = None  # 用于 categorical
    step: Optional[float] = None  # 可选步长

class OptimizationConfig(BaseModel):
    """优化任务的配置"""
    study_name: str
    direction: OptimizationDirection = OptimizationDirection.maximize
    sampler: SamplerType = SamplerType.tpe
    n_trials: int = 20
    # 参数空间定义
    search_space: Dict[str, ParameterDefinition]
    # 自定义初值 (模仿)
    initial_trials: List[Dict[str, Any]] = Field(default_factory=list)
    # 资源平衡配置 (可选)
    use_resource_balancing: bool = False
    resource_check_url: Optional[str] = None  # 获取可用资源的API

class StrategyParams(BaseModel):
    """传递给执行器的策略参数"""
    params: Dict[str, Any]
    trial_number: int
    study_name: str

class FeedbackData(BaseModel):
    """反馈数据模型"""
    trial_number: int
    study_name: str
    metric_name: str
    value: float
    timestamp: Optional[str] = None

class OptimizationStatus(BaseModel):
    """优化状态"""
    study_name: str
    status: str  # "running", "completed", "failed"
    current_trial: int
    best_value: Optional[float] = None
    best_params: Optional[Dict[str, Any]] = None