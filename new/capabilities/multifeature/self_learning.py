"""多特征自学习模块"""
from typing import Dict, Any, List, Optional, Set
from ..parallel.parallel_optimization_interface import ParallelOptimizationInterface
from .inference import induction, deduction
from .logic import HornClause
from .categories import TheoryCategory
import json
import os
import time


class RuleWithPriority:
    """
    带有优先级的规则类，用于冲突检测和优先级管理
    """
    def __init__(self, rule: Dict[str, Any]):
        self.rule = rule
        self.verification_score = 1.0  # 验证得分，根据规则的验证情况调整
        self.context_score = 1.0       # 上下文得分，根据规则的上下文适用性调整
        self.timestamp = time.time()   # 规则创建时间
        self.use_count = 0             # 规则使用次数
        # 从规则中获取置信度，如果没有则默认为1.0
        self.confidence = rule.get('confidence', 1.0)

    def priority(self, alpha=0.4, beta=0.4, gamma=0.2, lambd=0.01):
        """
        计算规则优先级
        alpha: 验证得分权重
        beta: 上下文得分权重
        gamma: 时间衰减权重
        lambd: 时间衰减因子
        """
        age_factor = 1.0
        if hasattr(self, 'last_used'):
            age_factor = max(0.1, 1.0 - lambd * (time.time() - self.timestamp))
        return alpha * self.verification_score + beta * self.context_score + gamma * age_factor


class KnowledgeBase:
    """
    知识库类，存储和管理自学习规则，支持冲突检测和优先级管理
    """
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化知识库
        
        Args:
            storage_path: 持久化存储路径
        """
        self.rules: List[RuleWithPriority] = []
        self.conflict_history = []  # 记录规则冲突历史
        self.storage_path = storage_path
        self._load_rules()
    
    def add_rules(self, new_rules: List[Dict[str, Any]]) -> None:
        """
        添加新规则到知识库，支持冲突检测和优先级管理
        
        Args:
            new_rules: 新规则列表
        """
        for rule in new_rules:
            new_wrapped = RuleWithPriority(rule)
            
            # 检查冲突
            conflicts = []
            for existing in self.rules:
                if self._would_conflict(rule, existing.rule):
                    conflicts.append(existing)

            if conflicts:
                print(f"Conflict detected: {rule.get('type')} rule vs {conflicts[0].rule.get('type')} rule")
                self.conflict_history.append((rule, [r.rule for r in conflicts]))

                # 优先级比较
                new_priority = new_wrapped.priority()
                old_priority = max(r.priority() for r in conflicts)
                if new_priority > old_priority:
                    print("→ New rule wins. Removing old rules.")
                    for r in conflicts:
                        self.rules.remove(r)
                    self.rules.append(new_wrapped)
                else:
                    print("→ Old rule wins. Discarding new rule.")
            else:
                # 检查是否存在相似规则
                if not self._has_similar_rule(rule):
                    self.rules.append(new_wrapped)
        
        # 保存规则到存储
        self._save_rules()
    
    def get_rules_by_type(self, rule_type: str) -> List[Dict[str, Any]]:
        """
        根据类型获取规则
        
        Args:
            rule_type: 规则类型
            
        Returns:
            规则列表
        """
        return [rule.rule for rule in self.rules if rule.rule.get('type') == rule_type]
    
    def get_applicable_rules(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取适用于当前上下文的规则
        
        Args:
            context: 当前上下文
            
        Returns:
            适用规则列表，按置信度排序
        """
        applicable = []
        
        for rule in self.rules:
            if self._is_rule_applicable(rule, context):
                applicable.append(rule)
        
        # 按置信度降序排序，然后返回实际规则字典
        return [rule.rule for rule in sorted(applicable, key=lambda x: x.confidence, reverse=True)]
    
    def update_rule_confidence(self, rule_index: int, new_confidence: float) -> bool:
        """
        更新规则置信度
        
        Args:
            rule_index: 规则索引
            new_confidence: 新的置信度值
            
        Returns:
            是否更新成功
        """
        if 0 <= rule_index < len(self.rules):
            self.rules[rule_index].confidence = new_confidence
            self.rules[rule_index].rule['confidence'] = new_confidence  # 更新内部规则字典
            self._save_rules()
            return True
        return False
    
    def clear_rules(self) -> None:
        """
        清空所有规则
        """
        self.rules = []
        if self.storage_path and os.path.exists(self.storage_path):
            os.remove(self.storage_path)
    
    def get_all_rules(self) -> List[Dict[str, Any]]:
        """
        获取所有规则（仅规则字典部分）
        """
        return [rule.rule for rule in self.rules]
    
    def get_theory(self) -> TheoryCategory:
        """
        获取当前知识库中的所有规则作为TheoryCategory
        """
        t = TheoryCategory()
        # 目前仅支持HornClause类型的规则，简单实现
        return t

    def _would_conflict(self, r1: Dict[str, Any], r2: Dict[str, Any]) -> bool:
        """
        检查两个规则是否会冲突
        简化：检查是否是同一类型规则且pattern相同但action不同
        """
        r1_type = r1.get('type')
        r2_type = r2.get('type')
        
        # 如果规则类型不同，不冲突
        if r1_type != r2_type:
            return False
            
        r1_pattern = r1.get('pattern', {})
        r2_pattern = r2.get('pattern', {})
        
        # 如果规则类型相同但pattern不同，不冲突
        if r1_pattern != r2_pattern:
            return False
            
        r1_action = r1.get('action')
        r2_action = r2.get('action')
        
        # 如果规则类型和pattern相同但action不同，冲突
        if r1_action != r2_action:
            return True
            
        return False

    def _has_similar_rule(self, rule: Dict[str, Any]) -> bool:
        """
        检查是否存在相似规则
        """
        rule_type = rule.get('type')
        rule_pattern = rule.get('pattern', {})
        
        for existing_rule in self.rules:
            if existing_rule.rule.get('type') == rule_type:
                existing_pattern = existing_rule.rule.get('pattern', {})
                # 简单相似性检查，可根据需要增强
                if rule_pattern == existing_pattern:
                    return True
        
        return False
    
    def _is_rule_applicable(self, rule: RuleWithPriority, context: Dict[str, Any]) -> bool:
        """
        检查规则是否适用于当前上下文
        """
        rule_dict = rule.rule
        # 基础实现：如果规则有pattern字段，检查上下文是否匹配
        if 'pattern' in rule_dict:
            pattern = rule_dict['pattern']
            if 'params' in pattern:
                # 检查必要参数是否存在
                for key, value in pattern['params'].items():
                    if key in context and context[key] != value:
                        return False
        
        # 检查条件表达式
        if 'condition' in rule_dict:
            # 简化实现，实际应用中可能需要更复杂的条件解析
            return True
        
        return True
    
    def _save_rules(self) -> None:
        """
        保存规则到文件
        """
        if self.storage_path:
            try:
                os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
                # 仅保存规则字典部分，不保存RuleWithPriority包装
                rules_to_save = [rule.rule for rule in self.rules]
                with open(self.storage_path, 'w', encoding='utf-8') as f:
                    json.dump(rules_to_save, f, ensure_ascii=False, indent=2)
            except Exception:
                # 保存失败时静默处理
                pass
    
    def _load_rules(self) -> None:
        """
        从文件加载规则
        """
        if self.storage_path and os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    loaded_rules = json.load(f)
                    # 为每个加载的规则创建RuleWithPriority对象
                    self.rules = [RuleWithPriority(rule_dict) for rule_dict in loaded_rules]
            except Exception:
                # 加载失败时使用空规则集
                self.rules = []
    
    def load_rules(self, rules: List[Dict[str, Any]]) -> None:
        """
        加载规则列表
        """
        self.rules = [RuleWithPriority(rule_dict) for rule_dict in rules]


class MultifeatureOptimizer(ParallelOptimizationInterface):
    """
    多特征自优化器实现
    基于归纳和演绎的自优化方法
    """
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化多特征自优化器
        
        Args:
            knowledge_base_path: 知识库存储路径
        """
        self.knowledge_base = KnowledgeBase(knowledge_base_path)
        self.history_data: List[Dict[str, Any]] = []
        self.best_parameters = None
        self.best_score = -float('inf')
    
    def optimize_task(self, task: Dict[str, Any], history_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        优化任务执行
        利用归纳和演绎进行任务优化
        """
        # 合并历史数据
        self.history_data.extend(history_data)
        
        # 使用归纳推理生成优化参数
        induction_result = induction(self.history_data)
        optimized_params = induction_result['optimized_params']
        
        # 获取适用于当前任务的规则
        applicable_rules = self.knowledge_base.get_applicable_rules(task.get('context', {}))
        
        # 应用规则调整参数
        for rule in applicable_rules:
            action = rule.get('action')
            if action == 'reinforce' and 'pattern' in rule:
                # 增强成功模式中的参数
                pattern_params = rule['pattern'].get('params', {})
                for key, value in pattern_params.items():
                    if key in optimized_params:
                        # 向成功值靠近
                        optimized_params[key] = (optimized_params[key] + value) / 2
            elif action == 'avoid' and 'pattern' in rule:
                # 避开失败模式中的参数
                pattern_params = rule['pattern'].get('params', {})
                for key in pattern_params:
                    if key in optimized_params:
                        # 尝试相反的值
                        optimized_params[key] = -optimized_params[key] if isinstance(optimized_params[key], (int, float)) else optimized_params[key]
        
        return {
            'optimized_params': optimized_params,
            'confidence': induction_result['confidence'],
            'applied_rules': len(applicable_rules),
            'data_points': induction_result.get('data_points', 0)
        }
    
    def learn_from_result(self, task_id: str, result: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> bool:
        """
        从执行结果和反馈中学习
        """
        try:
            # 记录结果到历史数据
            history_item = {
                'task_id': task_id,
                'result': result,
                'timestamp': self._get_current_timestamp()
            }
            
            if 'params' in result:
                history_item['params'] = result['params']
            
            self.history_data.append(history_item)
            
            # 使用演绎推理生成新规则
            new_rules = deduction(result, feedback)
            
            # 添加新规则到知识库
            if new_rules:
                self.knowledge_base.add_rules(new_rules)
            
            # 更新最佳参数记录
            result_score = self._calculate_result_score(result)
            if result_score > self.best_score:
                self.best_score = result_score
                if 'params' in result:
                    self.best_parameters = result['params']
            
            return True
        except Exception:
            return False
    
    def get_best_parameters(self) -> Optional[Dict[str, Any]]:
        """
        获取当前的最佳参数
        """
        if self.best_parameters:
            return {
                'parameters': self.best_parameters,
                'score': self.best_score,
                'rule_count': len(self.knowledge_base.rules)
            }
        return None
    
    def reset(self) -> bool:
        """
        重置优化器状态
        """
        try:
            self.history_data = []
            self.best_parameters = None
            self.best_score = -float('inf')
            return True
        except Exception:
            return False
    
    def save_state(self) -> Dict[str, Any]:
        """
        保存优化器状态
        """
        return {
            'history_data': self.history_data,
            'best_parameters': self.best_parameters,
            'best_score': self.best_score,
            'rules_count': len(self.knowledge_base.rules)
        }
    
    def load_state(self, state_data: Dict[str, Any]) -> bool:
        """
        加载优化器状态
        """
        try:
            if 'history_data' in state_data:
                self.history_data = state_data['history_data']
            if 'best_parameters' in state_data:
                self.best_parameters = state_data['best_parameters']
            if 'best_score' in state_data:
                self.best_score = state_data['best_score']
            return True
        except Exception:
            return False
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """
        获取优化统计信息
        """
        return {
            'history_data_count': len(self.history_data),
            'rules_count': len(self.knowledge_base.rules),
            'best_score': self.best_score,
            'success_rules_count': len(self.knowledge_base.get_rules_by_type('success_pattern')),
            'failure_rules_count': len(self.knowledge_base.get_rules_by_type('failure_pattern'))
        }
    
    def _calculate_result_score(self, result: Dict[str, Any]) -> float:
        """
        计算结果评分
        """
        # 从结果中提取评分
        if isinstance(result, (int, float)):
            return float(result)
        elif isinstance(result, dict):
            # 尝试常见的评分字段
            for field in ['score', 'quality', 'value', 'rating']:
                if field in result and isinstance(result[field], (int, float)):
                    return float(result[field])
            # 检查success字段
            if 'success' in result and result['success'] is True:
                return 1.0
        
        return 0.0
    
    def _get_current_timestamp(self) -> float:
        """
        获取当前时间戳
        """
        import time
        return time.time()
