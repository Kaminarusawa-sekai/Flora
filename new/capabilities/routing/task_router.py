"""任务路由器实现"""
from typing import Dict, Any, List, Optional, Tuple
from ..capability_base import CapabilityBase
import logging


class TaskRouter(CapabilityBase):
    """
    任务路由器
    负责根据任务特性选择最合适的执行器
    """
    
    def __init__(self):
        """
        初始化任务路由器
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.registry = None  # 将在initialize中设置
        self.routing_strategies = {
            'default': self._default_routing_strategy,
            'semantic_match': self._semantic_match_strategy,
            'load_balanced': self._load_balanced_strategy
        }
    
    def get_capability_type(self) -> str:
        """
        获取能力类型
        """
        return 'routing'
    
    def initialize(self, registry=None) -> bool:
        """
        初始化任务路由器
        
        Args:
            registry: Agent注册表，用于获取可用Agent信息
            
        Returns:
            bool: 是否初始化成功
        """
        if not super().initialize():
            return False
        
        self.registry = registry
        return True
    
    def select_best_actor(self, agent_id: str, context: Dict[str, Any]) -> Optional[str]:
        """
        从TaskCoordinator._select_best_actor迁移
        选择最合适的Agent来执行任务
        
        Args:
            agent_id: 当前Agent ID
            context: 任务上下文
            
        Returns:
            Optional[str]: 选定的Agent ID，如果没有找到则返回None
        """
        try:
            # 1. 确定使用的路由策略
            strategy_type = context.get('routing_strategy', 'default')
            strategy = self.routing_strategies.get(strategy_type, self.routing_strategies['default'])
            
            # 2. 获取候选Agent列表
            candidates = self._get_candidate_agents(agent_id, context)
            
            if not candidates:
                self.logger.warning(f"No candidate agents found for context: {context}")
                return None
            
            # 3. 应用路由策略选择最佳Agent
            best_agent_id = strategy(agent_id, context, candidates)
            
            if best_agent_id:
                self.logger.debug(f"Selected agent {best_agent_id} for context: {context}")
                return best_agent_id
            else:
                self.logger.warning(f"Failed to select agent for context: {context}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error selecting best actor: {str(e)}", exc_info=True)
            return None
    
    def _get_candidate_agents(self, agent_id: str, context: Dict[str, Any]) -> List[str]:
        """
        获取候选Agent列表
        
        Args:
            agent_id: 当前Agent ID
            context: 任务上下文
            
        Returns:
            List[str]: 候选Agent ID列表
        """
        if not self.registry:
            self.logger.error("Registry not initialized")
            return []
        
        try:
            # 根据任务类型和Agent关系获取候选列表
            task_type = context.get('task_type')
            
            # 1. 首先尝试获取当前Agent的直接子节点
            children = self.registry.get_children(agent_id) if agent_id else []
            
            if not children:
                self.logger.debug(f"No children for agent {agent_id}, checking siblings")
                # 2. 如果没有子节点，尝试获取兄弟节点
                parent = self.registry.get_parent(agent_id) if agent_id else None
                if parent:
                    children = self.registry.get_children(parent)
                    # 过滤掉自己
                    children = [child for child in children if child != agent_id]
            
            if not children:
                # 3. 如果仍然没有，获取所有叶子节点
                children = self._get_all_leaf_agents()
            
            # 4. 根据任务类型过滤候选Agent
            if task_type:
                filtered_candidates = []
                for candidate_id in children:
                    meta = self.registry.get_agent_meta(candidate_id)
                    if meta:
                        capabilities = meta.get('capability', [])
                        if task_type in capabilities or not capabilities:  # 允许无能力声明的Agent处理任何任务
                            filtered_candidates.append(candidate_id)
                return filtered_candidates
            
            return children
            
        except Exception as e:
            self.logger.error(f"Error getting candidate agents: {str(e)}", exc_info=True)
            return []
    
    def _default_routing_strategy(self, agent_id: str, context: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        """
        默认路由策略：选择第一个匹配的Agent
        
        Args:
            agent_id: 当前Agent ID
            context: 任务上下文
            candidates: 候选Agent列表
            
        Returns:
            Optional[str]: 选定的Agent ID
        """
        if not candidates:
            return None
        
        # 优先选择特定目标（如果指定）
        target = context.get('target_agent')
        if target and target in candidates:
            return target
        
        # 根据任务类型和Agent能力进行简单匹配
        task_type = context.get('task_type')
        if task_type:
            for candidate_id in candidates:
                meta = self.registry.get_agent_meta(candidate_id)
                if meta and task_type in meta.get('capability', []):
                    return candidate_id
        
        # 返回第一个候选Agent
        return candidates[0]
    
    def _semantic_match_strategy(self, agent_id: str, context: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        """
        语义匹配策略：基于Agent描述和任务上下文进行语义匹配
        
        Args:
            agent_id: 当前Agent ID
            context: 任务上下文
            candidates: 候选Agent列表
            
        Returns:
            Optional[str]: 选定的Agent ID
        """
        if not candidates:
            return None
        
        # 获取任务描述
        task_description = context.get('task_description', '')
        if not task_description:
            # 如果没有任务描述，使用默认策略
            return self._default_routing_strategy(agent_id, context, candidates)
        
        try:
            # 收集候选Agent的描述信息
            agent_descriptions = {}
            for candidate_id in candidates:
                meta = self.registry.get_agent_meta(candidate_id)
                if meta:
                    agent_descriptions[candidate_id] = {
                        'capabilities': meta.get('capability', []),
                        'description': meta.get('description', ''),
                        'datascope': meta.get('datascope', {})
                    }
            
            # 计算匹配度
            best_match = None
            best_score = 0
            
            for candidate_id, desc in agent_descriptions.items():
                score = self._calculate_semantic_score(task_description, desc)
                if score > best_score:
                    best_score = score
                    best_match = candidate_id
            
            # 如果最佳匹配得分高于阈值，则选择它
            if best_match and best_score > 0.3:  # 简单阈值
                return best_match
            else:
                # 否则使用默认策略
                return self._default_routing_strategy(agent_id, context, candidates)
                
        except Exception as e:
            self.logger.error(f"Error in semantic match strategy: {str(e)}", exc_info=True)
            return self._default_routing_strategy(agent_id, context, candidates)
    
    def _load_balanced_strategy(self, agent_id: str, context: Dict[str, Any], candidates: List[str]) -> Optional[str]:
        """
        负载均衡策略：选择当前负载最低的Agent
        
        Args:
            agent_id: 当前Agent ID
            context: 任务上下文
            candidates: 候选Agent列表
            
        Returns:
            Optional[str]: 选定的Agent ID
        """
        if not candidates:
            return None
        
        try:
            # 获取各Agent的负载信息
            agent_loads = {}
            for candidate_id in candidates:
                meta = self.registry.get_agent_meta(candidate_id)
                if meta:
                    # 获取当前负载或默认为0
                    load = meta.get('current_load', 0)
                    agent_loads[candidate_id] = load
            
            # 如果有负载信息，选择负载最低的
            if agent_loads:
                # 按负载排序，选择最低的
                sorted_agents = sorted(agent_loads.items(), key=lambda x: x[1])
                return sorted_agents[0][0]
            else:
                # 否则使用默认策略
                return self._default_routing_strategy(agent_id, context, candidates)
                
        except Exception as e:
            self.logger.error(f"Error in load balanced strategy: {str(e)}", exc_info=True)
            return self._default_routing_strategy(agent_id, context, candidates)
    
    def _calculate_semantic_score(self, task_description: str, agent_info: Dict[str, Any]) -> float:
        """
        计算任务描述与Agent信息的语义匹配得分
        
        Args:
            task_description: 任务描述
            agent_info: Agent信息，包含capabilities、description和datascope
            
        Returns:
            float: 匹配得分，范围0-1
        """
        # 简化的匹配算法，实际应用中可能需要使用更复杂的NLP方法
        score = 0
        task_lower = task_description.lower()
        
        # 检查能力匹配
        for capability in agent_info.get('capabilities', []):
            if capability.lower() in task_lower:
                score += 0.4  # 能力匹配权重较高
        
        # 检查描述匹配
        agent_desc = agent_info.get('description', '').lower()
        task_words = set(task_lower.split())
        desc_words = set(agent_desc.split())
        common_words = task_words.intersection(desc_words)
        if desc_words:
            score += 0.3 * len(common_words) / len(desc_words)  # 描述相似度
        
        # 检查数据范围匹配
        datascope = agent_info.get('datascope', {})
        for data_field in datascope:
            if data_field.lower() in task_lower:
                score += 0.3  # 数据范围匹配权重
        
        # 确保分数在0-1范围内
        return min(score, 1.0)
    
    def _get_all_leaf_agents(self) -> List[str]:
        """
        获取所有叶子节点Agent
        
        Returns:
            List[str]: 叶子节点Agent ID列表
        """
        if not self.registry:
            return []
        
        try:
            # 获取所有Agent
            all_agents = self.registry.get_all_agents()
            leaf_agents = []
            
            for agent_id in all_agents:
                # 检查是否有子节点
                children = self.registry.get_children(agent_id)
                if not children:
                    # 无子节点的视为叶子节点
                    meta = self.registry.get_agent_meta(agent_id)
                    if meta and meta.get('is_leaf', True):  # 也检查is_leaf标志
                        leaf_agents.append(agent_id)
            
            return leaf_agents
            
        except Exception as e:
            self.logger.error(f"Error getting leaf agents: {str(e)}", exc_info=True)
            return []
    
    def register_routing_strategy(self, strategy_name: str, strategy_function) -> bool:
        """
        注册自定义路由策略
        
        Args:
            strategy_name: 策略名称
            strategy_function: 策略函数，签名为(agent_id, context, candidates) -> Optional[str]
            
        Returns:
            bool: 是否注册成功
        """
        if not callable(strategy_function):
            self.logger.error(f"Strategy function must be callable")
            return False
        
        self.routing_strategies[strategy_name] = strategy_function
        self.logger.info(f"Registered routing strategy: {strategy_name}")
        return True
    
    def get_routing_strategies(self) -> List[str]:
        """
        获取所有可用的路由策略
        
        Returns:
            List[str]: 路由策略名称列表
        """
        return list(self.routing_strategies.keys())
