"""优化消息模块"""
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from .base_message import BaseMessage
from .task_messages import TaskMessage


class OptimizationMessage(TaskMessage):
    """
    优化相关消息的基类
    """
    
    def __init__(self, message_type: str, source: str, destination: str, task_id: str, optimization_id: str, timestamp: Optional[datetime] = None):
        """
        初始化优化消息
        
        Args:
            message_type: 消息类型
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            optimization_id: 优化ID
            timestamp: 时间戳
        """
        super().__init__(message_type, source, destination, task_id, timestamp)
        self.optimization_id = optimization_id
    
    def _generate_id(self) -> str:
        """
        生成消息ID
        """
        import uuid
        return f"opt_msg_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "optimization_id": self.optimization_id
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationMessage':
        """
        从字典创建优化消息
        """
        message = super().from_dict(data)
        message.optimization_id = data.get('optimization_id', '')
        return message


class OptimizationStartedMessage(OptimizationMessage):
    """
    优化开始消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, optimization_id: str, optimization_type: str, initial_params: Dict[str, Any], constraints: Optional[Dict[str, Any]] = None, objective: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        初始化优化开始消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            optimization_id: 优化ID
            optimization_type: 优化类型
            initial_params: 初始参数
            constraints: 约束条件
            objective: 优化目标
            timestamp: 时间戳
        """
        super().__init__('optimization_started', source, destination, task_id, optimization_id, timestamp)
        self.optimization_type = optimization_type
        self.initial_params = initial_params
        self.constraints = constraints or {}
        self.objective = objective
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "optimization_type": self.optimization_type,
            "initial_params": self.initial_params,
            "constraints": self.constraints,
            "objective": self.objective
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationStartedMessage':
        """
        从字典创建优化开始消息
        """
        message = super().from_dict(data)
        message.optimization_type = data.get('optimization_type', '')
        message.initial_params = data.get('initial_params', {})
        message.constraints = data.get('constraints', {})
        message.objective = data.get('objective')
        return message


class OptimizationCompletedMessage(OptimizationMessage):
    """
    优化完成消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, optimization_id: str, best_params: Dict[str, Any], best_score: float, iterations: int, optimization_time: float, timestamp: Optional[datetime] = None):
        """
        初始化优化完成消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            optimization_id: 优化ID
            best_params: 最优参数
            best_score: 最优得分
            iterations: 迭代次数
            optimization_time: 优化时间（秒）
            timestamp: 时间戳
        """
        super().__init__('optimization_completed', source, destination, task_id, optimization_id, timestamp)
        self.best_params = best_params
        self.best_score = best_score
        self.iterations = iterations
        self.optimization_time = optimization_time
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "best_params": self.best_params,
            "best_score": self.best_score,
            "iterations": self.iterations,
            "optimization_time": self.optimization_time
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationCompletedMessage':
        """
        从字典创建优化完成消息
        """
        message = super().from_dict(data)
        message.best_params = data.get('best_params', {})
        message.best_score = data.get('best_score', 0.0)
        message.iterations = data.get('iterations', 0)
        message.optimization_time = data.get('optimization_time', 0.0)
        return message


class OptimizationFailedMessage(OptimizationMessage):
    """
    优化失败消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, optimization_id: str, error: str, details: Optional[Dict[str, Any]] = None, iterations: int = 0, timestamp: Optional[datetime] = None):
        """
        初始化优化失败消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            optimization_id: 优化ID
            error: 错误信息
            details: 错误详情
            iterations: 已执行迭代次数
            timestamp: 时间戳
        """
        super().__init__('optimization_failed', source, destination, task_id, optimization_id, timestamp)
        self.error = error
        self.details = details or {}
        self.iterations = iterations
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "error": self.error,
            "details": self.details,
            "iterations": self.iterations
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationFailedMessage':
        """
        从字典创建优化失败消息
        """
        message = super().from_dict(data)
        message.error = data.get('error', '')
        message.details = data.get('details', {})
        message.iterations = data.get('iterations', 0)
        return message


class ParameterUpdatedMessage(OptimizationMessage):
    """
    参数更新消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, optimization_id: str, iteration: int, updated_params: Dict[str, Any], current_score: float, improvement: float, timestamp: Optional[datetime] = None):
        """
        初始化参数更新消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            optimization_id: 优化ID
            iteration: 当前迭代次数
            updated_params: 更新后的参数
            current_score: 当前得分
            improvement: 改进幅度
            timestamp: 时间戳
        """
        super().__init__('parameter_updated', source, destination, task_id, optimization_id, timestamp)
        self.iteration = iteration
        self.updated_params = updated_params
        self.current_score = current_score
        self.improvement = improvement
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "iteration": self.iteration,
            "updated_params": self.updated_params,
            "current_score": self.current_score,
            "improvement": self.improvement
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ParameterUpdatedMessage':
        """
        从字典创建参数更新消息
        """
        message = super().from_dict(data)
        message.iteration = data.get('iteration', 0)
        message.updated_params = data.get('updated_params', {})
        message.current_score = data.get('current_score', 0.0)
        message.improvement = data.get('improvement', 0.0)
        return message


class OptimizationProgressMessage(OptimizationMessage):
    """
    优化进度消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, optimization_id: str, iteration: int, progress: float, current_score: float, best_score: float, status: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        初始化优化进度消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            optimization_id: 优化ID
            iteration: 当前迭代次数
            progress: 优化进度（0-1）
            current_score: 当前得分
            best_score: 当前最优得分
            status: 状态描述
            timestamp: 时间戳
        """
        super().__init__('optimization_progress', source, destination, task_id, optimization_id, timestamp)
        self.iteration = iteration
        self.progress = min(max(0.0, progress), 1.0)  # 确保进度在0-1范围内
        self.current_score = current_score
        self.best_score = best_score
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "iteration": self.iteration,
            "progress": self.progress,
            "current_score": self.current_score,
            "best_score": self.best_score,
            "status": self.status
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationProgressMessage':
        """
        从字典创建优化进度消息
        """
        message = super().from_dict(data)
        message.iteration = data.get('iteration', 0)
        message.progress = data.get('progress', 0.0)
        message.current_score = data.get('current_score', 0.0)
        message.best_score = data.get('best_score', 0.0)
        message.status = data.get('status')
        return message


class OptimizationConvergedMessage(OptimizationMessage):
    """
    优化收敛消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, optimization_id: str, iteration: int, best_params: Dict[str, Any], best_score: float, convergence_criterion: float, timestamp: Optional[datetime] = None):
        """
        初始化优化收敛消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            optimization_id: 优化ID
            iteration: 当前迭代次数
            best_params: 最优参数
            best_score: 最优得分
            convergence_criterion: 收敛阈值
            timestamp: 时间戳
        """
        super().__init__('optimization_converged', source, destination, task_id, optimization_id, timestamp)
        self.iteration = iteration
        self.best_params = best_params
        self.best_score = best_score
        self.convergence_criterion = convergence_criterion
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "iteration": self.iteration,
            "best_params": self.best_params,
            "best_score": self.best_score,
            "convergence_criterion": self.convergence_criterion
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'OptimizationConvergedMessage':
        """
        从字典创建优化收敛消息
        """
        message = super().from_dict(data)
        message.iteration = data.get('iteration', 0)
        message.best_params = data.get('best_params', {})
        message.best_score = data.get('best_score', 0.0)
        message.convergence_criterion = data.get('convergence_criterion', 0.0)
        return message
