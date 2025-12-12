"""基于Optuna的并行执行优化器"""
import optuna
from typing import List, Dict, Any, Tuple, Optional
from abc import ABC, abstractmethod
from ..capability_base import CapabilityBase
from ..dimension.dimension_parser import DimensionParserCapability
from .parallel_optimization_interface import (ParallelOptimizationInterface,
                                              OptimizationOrchestratorInterface,
                                              ExecutionManagerInterface)


class OptunaOptimizer(CapabilityBase, ParallelOptimizationInterface):
    """
    基于Optuna的并行执行优化器
    提供多维度参数空间自动探索和优化能力
    """
    
    def __init__(self, direction: str = "maximize", max_concurrent: int = 4):
        """
        初始化Optuna优化器
        
        Args:
            direction: 优化方向，"maximize"或"minimize"
            max_concurrent: 最大并发执行任务数
        """
        super().__init__()
        self.study = optuna.create_study(direction=direction)
        self.max_concurrent = max_concurrent
        self.vector_dim = 0
        self.trial_results = {}
        self.dimension_parser = None
    
    def get_capability_type(self) -> str:
        """获取能力类型"""
        return "optimization_optuna"
    
    def set_dimension_parser(self, dimension_parser: DimensionParserCapability) -> None:
        """
        设置维度解析器
        
        Args:
            dimension_parser: 维度解析器实例
        """
        self.dimension_parser = dimension_parser
    
    def initialize_optimization_space(self, vector_dim: int) -> None:
        """
        初始化优化空间维度
        
        Args:
            vector_dim: 优化向量维度
        """
        self.vector_dim = vector_dim
    
    def suggest_parameters(self, batch_size: int) -> List[Tuple[optuna.Trial, List[float]]]:
        """
        批量建议参数组合
        
        Args:
            batch_size: 批量大小
            
        Returns:
            包含trial对象和参数向量的列表
        """
        trials = []
        for _ in range(min(batch_size, self.max_concurrent)):
            trial = self.study.ask()
            # 在[-1,1]^D空间采样参数
            vector = [trial.suggest_float(f"x{i}", -1.0, 1.0) for i in range(self.vector_dim)]
            trials.append((trial, vector))
        return trials
    
    def update_optimization_results(self, trials_results: List[Tuple[optuna.Trial, float]]) -> None:
        """
        更新优化结果
        
        Args:
            trials_results: trial对象和对应评分的列表
        """
        for trial, score in trials_results:
            self.study.tell(trial, score)
            self.trial_results[trial.number] = {
                'score': score,
                'params': trial.params
            }
    
    def get_best_parameters(self) -> Dict[str, Any]:
        """
        获取最佳参数
        
        Returns:
            最佳参数字典
        """
        if self.study.best_params:
            # 将Optuna参数格式转换为向量格式
            vector = [self.study.best_params[f"x{i}"] for i in range(self.vector_dim)]
            return {
                "vector": vector,
                "value": self.study.best_value,
                "params": self.study.best_params,
                "trial_number": self.study.best_trial.number
            }
        return None
    
    def get_trial_count(self) -> int:
        """
        获取已执行的试验次数
        
        Returns:
            int: 试验次数
        """
        return len(self.study.trials)
    
    def get_optimization_history(self) -> List[Dict[str, Any]]:
        """
        获取优化历史记录
        
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        history = []
        for trial in self.study.trials:
            if trial.state == optuna.trial.TrialState.COMPLETE:
                vector = [trial.params.get(f"x{i}", 0.0) for i in range(self.vector_dim)]
                history.append({
                    'trial_number': trial.number,
                    'value': trial.value,
                    'vector': vector,
                    'params': trial.params,
                    'datetime_start': trial.datetime_start,
                    'datetime_complete': trial.datetime_complete
                })
        return history


# 与LLM集成的优化协调器
class OptimizationOrchestrator(CapabilityBase, OptimizationOrchestratorInterface):
    """
    优化协调器，负责LLM与优化器的集成
    """
    
    def __init__(self, user_goal: str, direction: str = "maximize", max_concurrent: int = 4):
        """
        初始化优化协调器
        
        Args:
            user_goal: 用户目标
            direction: 优化方向，"maximize"或"minimize"
            max_concurrent: 最大并发执行任务数
        """
        super().__init__()
        self.user_goal = user_goal
        
        # 创建维度解析器
        self.dimension_parser = DimensionParserCapability(user_goal)
        
        # 创建Optuna优化器
        self.optimizer = OptunaOptimizer(direction, max_concurrent)
        self.optimizer.set_dimension_parser(self.dimension_parser)
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        
        Returns:
            str: 能力类型标识符
        """
        return "optimization_orchestrator"
    
    def discover_optimization_dimensions(self) -> Dict[str, Any]:
        """
        自动发现优化维度
        
        Returns:
            包含维度信息的字典
        """
        schema = self.dimension_parser.discover_schema()
        # 初始化优化空间
        self.optimizer.initialize_optimization_space(len(schema['dimensions']))
        return schema
    
    def vector_to_instruction(self, vector: List[float]) -> str:
        """
        将参数向量转换为执行指令
        
        Args:
            vector: 参数向量
            
        Returns:
            执行指令字符串
        """
        return self.dimension_parser.vector_to_instruction(vector)
    
    def evaluate_output(self, output: str) -> Dict[str, Any]:
        """
        评估执行输出并返回评分
        
        Args:
            output: 执行输出内容
            
        Returns:
            包含评分和反馈的字典
        """
        return self.dimension_parser.output_to_score(output)
    
    def get_optimization_instructions(self, batch_size: int = 3) -> Dict[str, Any]:
        """
        获取优化指令批次
        
        Args:
            batch_size: 批量大小
            
        Returns:
            包含trials和对应指令的字典
        """
        # 获取参数建议
        trials_params = self.optimizer.suggest_parameters(batch_size)
        
        # 转换为指令
        trial_instructions = []
        for trial, vector in trials_params:
            instruction = self.vector_to_instruction(vector)
            trial_instructions.append({
                'trial': trial,
                'trial_number': trial.number,
                'vector': vector,
                'instruction': instruction
            })
            # 保存指令到维度解析器的历史记录
            self.dimension_parser.set_last_instruction(instruction)
        
        return {
            'trials': trial_instructions,
            'total_count': len(trial_instructions)
        }
    
    def process_execution_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        处理执行结果并更新优化器
        
        Args:
            results: 包含trial_number, output的执行结果列表
            
        Returns:
            更新后的优化状态
        """
        trial_results = []
        
        # 评估每个执行结果
        for result in results:
            trial_number = result.get('trial_number')
            output = result.get('output', '')
            
            # 获取对应的trial对象
            trial = None
            for study_trial in self.optimizer.study.trials:
                if study_trial.number == trial_number:
                    trial = study_trial
                    break
            
            if trial:
                # 评估输出并获取分数
                evaluation = self.evaluate_output(output)
                trial_results.append((trial, evaluation['score']))
        
        # 更新优化结果
        self.optimizer.update_optimization_results(trial_results)
        
        # 返回当前最佳参数
        return {
            'best_params': self.optimizer.get_best_parameters(),
            'trial_count': self.optimizer.get_trial_count(),
            'processed_count': len(trial_results)
        }



