"""决策引擎适配器"""
from typing import Dict, Any, List, Optional
from ..capability_base import CapabilityBase


class DecisionEngineAdapter(CapabilityBase):
    """
    决策引擎适配器
    提供决策支持功能，基于change_orchestrator的决策逻辑
    """
    
    def __init__(self):
        """
        初始化决策引擎适配器
        """
        super().__init__()
        self.rules = []
        self.decision_history = []
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'decision'
    
    def initialize(self) -> bool:
        """
        初始化决策引擎
        """
        if not super().initialize():
            return False
        
        # 初始化默认规则
        self._load_default_rules()
        return True
    
    def make_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        基于上下文做出决策
        
        Args:
            context: 决策上下文
            
        Returns:
            Dict[str, Any]: 决策结果
        """
        # 应用规则引擎
        applicable_rules = self._get_applicable_rules(context)
        decision = self._evaluate_rules(applicable_rules, context)
        
        # 记录决策历史
        decision_record = {
            'timestamp': self._get_current_timestamp(),
            'context': context,
            'decision': decision,
            'applied_rules': [rule['id'] for rule in applicable_rules]
        }
        self.decision_history.append(decision_record)
        
        # 限制历史记录长度
        if len(self.decision_history) > 1000:
            self.decision_history = self.decision_history[-1000:]
        
        return decision
    
    def add_rule(self, rule: Dict[str, Any]) -> bool:
        """
        添加决策规则
        
        Args:
            rule: 规则定义，包含id, condition, action等字段
            
        Returns:
            bool: 是否添加成功
        """
        if 'id' not in rule or 'condition' not in rule or 'action' not in rule:
            return False
        
        # 检查是否已存在同名规则
        for i, existing_rule in enumerate(self.rules):
            if existing_rule['id'] == rule['id']:
                # 更新现有规则
                self.rules[i] = rule
                return True
        
        # 添加新规则
        self.rules.append(rule)
        return True
    
    def remove_rule(self, rule_id: str) -> bool:
        """
        移除决策规则
        
        Args:
            rule_id: 规则ID
            
        Returns:
            bool: 是否移除成功
        """
        for i, rule in enumerate(self.rules):
            if rule['id'] == rule_id:
                del self.rules[i]
                return True
        return False
    
    def get_rules(self) -> List[Dict[str, Any]]:
        """
        获取所有规则
        
        Returns:
            List[Dict[str, Any]]: 规则列表
        """
        return self.rules.copy()
    
    def evaluate_scenario(self, scenario: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        评估场景，返回所有可能的决策路径
        
        Args:
            scenario: 场景描述
            
        Returns:
            List[Dict[str, Any]]: 决策路径列表
        """
        paths = []
        applicable_rules = self._get_applicable_rules(scenario)
        
        for rule in applicable_rules:
            # 模拟应用每个规则的结果
            action_result = self._simulate_action(rule['action'], scenario)
            paths.append({
                'rule_id': rule['id'],
                'rule_name': rule.get('name', rule['id']),
                'action': rule['action'],
                'result': action_result,
                'confidence': rule.get('confidence', 0.5)
            })
        
        # 按置信度排序
        return sorted(paths, key=lambda x: x['confidence'], reverse=True)
    
    def _get_applicable_rules(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        获取适用于当前上下文的规则
        """
        applicable = []
        
        for rule in self.rules:
            if self._evaluate_condition(rule['condition'], context):
                applicable.append(rule)
        
        # 按优先级排序
        return sorted(applicable, key=lambda x: x.get('priority', 0), reverse=True)
    
    def _evaluate_condition(self, condition: Any, context: Dict[str, Any]) -> bool:
        """
        评估条件是否满足
        
        Args:
            condition: 条件表达式
            context: 上下文数据
            
        Returns:
            bool: 条件是否满足
        """
        if isinstance(condition, dict):
            # 复杂条件：AND/OR/NOT
            if 'AND' in condition:
                return all(self._evaluate_condition(c, context) for c in condition['AND'])
            elif 'OR' in condition:
                return any(self._evaluate_condition(c, context) for c in condition['OR'])
            elif 'NOT' in condition:
                return not self._evaluate_condition(condition['NOT'], context)
            elif '==' in condition:
                key, value = condition['==']
                return context.get(key) == value
            elif '!=' in condition:
                key, value = condition['!=']
                return context.get(key) != value
            elif '>' in condition:
                key, value = condition['>']
                return context.get(key, 0) > value
            elif '<' in condition:
                key, value = condition['<']
                return context.get(key, 0) < value
            elif '>=' in condition:
                key, value = condition['>=']
                return context.get(key, 0) >= value
            elif '<=' in condition:
                key, value = condition['<=']
                return context.get(key, 0) <= value
            elif 'in' in condition:
                key, values = condition['in']
                return context.get(key) in values
        
        # 默认返回False
        return False
    
    def _evaluate_rules(self, rules: List[Dict[str, Any]], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        评估规则并生成决策
        """
        if not rules:
            # 无适用规则时的默认决策
            return self._get_default_decision(context)
        
        # 应用第一个规则（优先级最高的）
        rule = rules[0]
        action = rule['action']
        
        # 执行动作
        result = self._execute_action(action, context)
        
        return {
            'action': action,
            'result': result,
            'rule_id': rule['id'],
            'confidence': rule.get('confidence', 0.5),
            'timestamp': self._get_current_timestamp()
        }
    
    def _execute_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行决策动作
        """
        action_type = action.get('type', 'default')
        
        if action_type == 'route':
            # 路由动作
            target = action.get('target', 'default')
            return {
                'target': target,
                'parameters': action.get('parameters', {})
            }
        elif action_type == 'transform':
            # 转换动作
            return self._transform_context(action, context)
        elif action_type == 'call':
            # 调用动作
            return {
                'function': action.get('function', ''),
                'arguments': action.get('arguments', {})
            }
        else:
            # 默认动作
            return action.get('result', {})
    
    def _transform_context(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        转换上下文
        """
        transformations = action.get('transformations', [])
        result = context.copy()
        
        for transform in transformations:
            if 'set' in transform:
                key, value = transform['set']
                result[key] = value
            elif 'delete' in transform:
                key = transform['delete']
                if key in result:
                    del result[key]
            elif 'update' in transform:
                key, expr = transform['update']
                if key in result:
                    # 简单表达式处理，实际应用中可能需要更复杂的表达式引擎
                    result[key] = expr
        
        return result
    
    def _simulate_action(self, action: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        模拟执行动作（用于场景评估）
        """
        return self._execute_action(action, context)
    
    def _get_default_decision(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        获取默认决策
        """
        return {
            'action': {
                'type': 'default',
                'result': 'no_action'
            },
            'rule_id': 'default',
            'confidence': 0.1
        }
    
    def _load_default_rules(self) -> None:
        """
        加载默认规则
        """
        default_rules = [
            {
                'id': 'high_priority_route',
                'name': '高优先级任务路由',
                'condition': {'==': ['priority', 'high']},
                'action': {
                    'type': 'route',
                    'target': 'high_priority_queue',
                    'parameters': {'priority': 'high'}
                },
                'priority': 100,
                'confidence': 0.9
            },
            {
                'id': 'complex_task_route',
                'name': '复杂任务路由',
                'condition': {'>': ['complexity', 0.7]},
                'action': {
                    'type': 'route',
                    'target': 'expert_agent',
                    'parameters': {'mode': 'detailed'}
                },
                'priority': 80,
                'confidence': 0.8
            },
            {
                'id': 'simple_task_transform',
                'name': '简单任务转换',
                'condition': {'<=': ['complexity', 0.3]},
                'action': {
                    'type': 'transform',
                    'transformations': [
                        {'set': ['processing_mode', 'fast']}
                    ]
                },
                'priority': 60,
                'confidence': 0.7
            }
        ]
        
        self.rules.extend(default_rules)
    
    def _get_current_timestamp(self) -> float:
        """
        获取当前时间戳
        """
        import time
        return time.time()
