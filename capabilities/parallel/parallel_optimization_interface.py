"""并行超参数调优接口定义"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
import optuna


class ParallelOptimizationInterface(ABC):
    """
    并行超参数调优抽象接口
    定义并行优化器的标准方法
    """
    
    @abstractmethod
    def __init__(self, direction: str = "maximize", max_concurrent: int = 4):
        """
        初始化并行优化器
        
        Args:
            direction: 优化方向，"maximize"或"minimize"
            max_concurrent: 最大并发执行任务数
        """
        pass
    
    @abstractmethod
    def get_capability_type(self) -> str:
        """
        获取能力类型
        
        Returns:
            能力类型标识符
        """
        pass
    
    @abstractmethod
    def initialize_optimization_space(self, vector_dim: int) -> None:
        """
        初始化优化空间维度
        
        Args:
            vector_dim: 优化向量维度
        """
        pass
    
    @abstractmethod
    def suggest_parameters(self, batch_size: int) -> List[Tuple[optuna.Trial, List[float]]]:
        """
        批量建议参数组合
        
        Args:
            batch_size: 批量大小
            
        Returns:
            包含trial对象和参数向量的列表
        """
        pass
    
    @abstractmethod
    def update_optimization_results(self, trials_results: List[Tuple[optuna.Trial, float]]) -> None:
        """
        更新优化结果
        
        Args:
            trials_results: trial对象和对应评分的列表
        """
        pass
    
    @abstractmethod
    def get_best_parameters(self) -> Dict[str, Any]:
        """
        获取最佳参数
        
        Returns:
            最佳参数字典
        """
        pass
    
    @abstractmethod
    def get_trial_count(self) -> int:
        """
        获取已执行的试验次数
        
        Returns:
            int: 试验次数
        """
        pass
    
    @abstractmethod
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """
        获取优化历史记录
        
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        pass


class ExecutionManagerInterface(ABC):
    """
    执行管理器抽象接口
    定义批量执行指令的标准方法
    """
    
    @abstractmethod
    def run_batch(self, instructions: List[str], trial_numbers: List[int]) -> Dict[str, Any]:
        """
        批量执行指令
        
        Args:
            instructions: 指令列表
            trial_numbers: 试验编号列表
            
        Returns:
            包含执行结果的字典
        """
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """
        获取执行管理器状态
        
        Returns:
            状态信息字典
        """
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """
        关闭执行管理器
        """
        pass


class OptimizationOrchestratorInterface(ABC):
    """
    优化协调器接口
    负责LLM与优化器的集成和协调
    """
    
    @abstractmethod
    def __init__(self, user_goal: str, direction: str = "maximize", max_concurrent: int = 4):
        """
        初始化优化协调器
        
        Args:
            user_goal: 用户目标
            direction: 优化方向，"maximize"或"minimize"
            max_concurrent: 最大并发执行任务数
        """
        pass
    
    @abstractmethod
    def get_capability_type(self) -> str:
        """
        获取能力类型
        
        Returns:
            str: 能力类型标识符
        """
        pass
    
    @abstractmethod
    def discover_optimization_dimensions(self) -> Dict[str, Any]:
        """
        自动发现优化维度
        
        Returns:
            包含维度信息的字典
        """
        pass
    
    @abstractmethod
    def vector_to_instruction(self, vector: List[float]) -> str:
        """
        将参数向量转换为执行指令
        
        Args:
            vector: 参数向量
            
        Returns:
            执行指令字符串
        """
        pass
    
    @abstractmethod
    def evaluate_output(self, output: str) -> Dict[str, Any]:
        """
        评估执行输出并返回评分
        
        Args:
            output: 执行输出内容
            
        Returns:
            包含评分和反馈的字典
        """
        pass
    
    @abstractmethod
    def get_optimization_instructions(self, batch_size: int = 3) -> Dict[str, Any]:
        """
        获取优化指令批次
        
        Args:
            batch_size: 批量大小
            
        Returns:
            包含trials和对应指令的字典
        """
        pass
    
    @abstractmethod
    def process_execution_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理执行结果并更新优化器
        
        Args:
            results: 包含trial_number, output的执行结果列表
            
        Returns:
            更新后的优化状态
        """
        pass
