from abc import ABC
from typing import Dict, Any, List, Optional
from .optimization_interface import OptimizationInterface
from ..multifeature import (
    KnowledgeBase,
    TheoryCategory,
    deduction, induction,
    run_pc_algorithm, orient_edges,
    llm_causal_direction
)

class MultiFeatureOptimizer(OptimizationInterface):
    """多特征优化器实现"""
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化多特征优化器"""
        self.config = config or {}
        # 初始化知识库
        self.knowledge_base = KnowledgeBase(storage_path=self.config.get('knowledge_base_path'))
        self.trial_count = 0
        self.best_parameters = None
        self.best_score = float('-inf')
        self.optimization_history = []
    
    def optimize_task(self, task: Dict[str, Any], history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """执行任务参数优化"""
        self.trial_count += 1
        
        # 使用知识库优化参数
        context = {
            'task_name': task.get('task_name'),
            'current_state': task.get('current_state', {}),
            'constraints': task.get('constraints', {}),
            'previous_trial': self.trial_count - 1,
            'history_data': history_data  # 将历史数据传入上下文
        }
        
        # 获取适用规则
        applicable_rules = self.knowledge_base.get_applicable_rules(context)
        optimized_params = self.config.get('default_parameters', {}).copy()
        
        # 应用规则到当前参数
        for rule in applicable_rules:
            rule_type = rule.get('type')
            params = rule.get('pattern', {}).get('params', {})
            action = rule.get('action', {})
            
            if rule_type == 'success_pattern':
                # 成功模式：增加参数值
                for param, value in params.items():
                    if param in optimized_params:
                        optimized_params[param] *= action.get('factor', 1.1)
            elif rule_type == 'failure_pattern':
                # 失败模式：减少参数值
                for param, value in params.items():
                    if param in optimized_params:
                        optimized_params[param] *= action.get('factor', 0.9)
        
        # 结合约束条件确保参数在允许范围内
        constraints = task.get('constraints', {})
        for param_name, (min_val, max_val) in constraints.items():
            if param_name in optimized_params:
                optimized_params[param_name] = max(min(optimized_params[param_name], max_val), min_val)
        
        # 记录优化历史
        self.optimization_history.append({
            'trial': self.trial_count,
            'parameters': optimized_params,
            'task_context': context
        })
        
        return optimized_params
    
    def learn_from_result(self, task_id: str, result: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> bool:
        """从执行结果中学习并更新知识库"""
        try:
            # 提取必要的信息
            parameters = result.get('parameters', {})
            result_score = result.get('score', 0.0)
            task_context = result.get('context', {})
            
            # 根据结果创建新规则
            rule_type = 'success_pattern' if result_score > 0.7 else 'failure_pattern'
            
            # 创建新规则
            new_rule = {
                'type': rule_type,
                'pattern': {
                    'task_name': task_context.get('task_name'),
                    'params': parameters,
                    'result_score': result_score
                },
                'action': {
                    'adjustment': 'increase' if rule_type == 'success_pattern' else 'decrease',
                    'factor': 1.1 if rule_type == 'success_pattern' else 0.9
                },
                'priority': result_score  # 使用结果分数作为优先级
            }
            
            # 将新规则添加到知识库
            added = self.knowledge_base.add_rules([new_rule])
            
            # 更新最佳参数记录
            if result_score > self.best_score:
                self.best_score = result_score
                self.best_parameters = parameters
                
            return added
        except Exception as e:
            return False
    
    def get_best_parameters(self) -> Optional[Dict[str, Any]]:
        """获取当前的最佳参数"""
        return self.best_parameters
    
    def reset(self) -> bool:
        """重置优化器状态"""
        try:
            self.trial_count = 0
            self.best_parameters = self.config.get('default_parameters')
            self.best_score = float('-inf')
            self.optimization_history = []
            self.knowledge_base.clear_rules()
            return True
        except Exception as e:
            return False
    
    def save_state(self) -> Dict[str, Any]:
        """保存优化器状态"""
        return {
            'config': self.config,
            'trial_count': self.trial_count,
            'best_parameters': self.best_parameters,
            'best_score': self.best_score,
            'optimization_history': self.optimization_history,
            'knowledge_base_state': self.knowledge_base.get_all_rules()  # 保存知识库规则
        }
    
    def load_state(self, state_data: Dict[str, Any]) -> bool:
        """加载优化器状态"""
        try:
            self.config.update(state_data.get('config', {}))
            self.trial_count = state_data.get('trial_count', 0)
            self.best_parameters = state_data.get('best_parameters', self.config.get('default_parameters'))
            self.best_score = state_data.get('best_score', float('-inf'))
            self.optimization_history = state_data.get('optimization_history', [])
            # 加载知识库状态时需要重新初始化知识库并加载规则
            self.knowledge_base = KnowledgeBase(storage_path=self.config.get('knowledge_base_path'))
            if state_data.get('knowledge_base_state'):
                self.knowledge_base.load_rules(state_data.get('knowledge_base_state'))  # 使用load_rules方法加载规则
            return True
        except Exception as e:
            return False
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        return {
            'trial_count': self.trial_count,
            'best_parameters': self.best_parameters,
            'best_score': self.best_score,
            'history_length': len(self.optimization_history),
            'rule_count': len(self.knowledge_base.rules)
        }

