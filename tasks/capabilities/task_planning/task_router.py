"""任务路由器实现"""
from typing import Dict, Any, List, Optional, Tuple
from ..capability_base import CapabilityBase
import logging

class TaskRouter(CapabilityBase):
    """任务路由器（支持自然语言输入 + 记忆上下文字符串）"""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self.tree_manager = None
        self._llm = None
        self.routing_strategies = {
            'default': self._default_routing_strategy,
            'semantic_match': self._semantic_match_strategy,
            'load_balanced': self._load_balanced_strategy,
            'qwen_intelligent': self._qwen_intelligent_strategy,
        }

    def get_capability_type(self) -> str:
        return 'routing'

    def initialize(self, tree_manager=None, llm_client=None) -> bool:
        if not super().initialize():
            return False
        self.tree_manager = tree_manager
        self._llm = llm_client
        return True

    def select_best_actor(
        self,
        agent_id: str,
        user_input: str,
        memory_context: Optional[str] = None,
        strategy: str = 'qwen_intelligent'
    ) -> Optional[str]:
        """
        基于自然语言输入和记忆上下文选择最佳执行者
        
        Args:
            agent_id (str): 当前协调者 Agent ID
            user_input (str): 用户的自然语言输入（如“分析最近的销售数据”）
            memory_context (Optional[str]): 由 MemoryManager.build_conversation_context() 生成的记忆上下文
            strategy (str): 路由策略，默认使用 qwen_intelligent
            
        Returns:
            Optional[str]: 选中的子 Agent ID
        """
        try:
            candidates = self._get_candidate_agents(agent_id)
            if not candidates:
                self.logger.warning("No candidate agents available.")
                return None

            strategy_func = self.routing_strategies.get(strategy)
            if not strategy_func:
                self.logger.warning(f"Unknown strategy '{strategy}', fallback to 'qwen_intelligent'")
                strategy_func = self.routing_strategies['qwen_intelligent']

            best_agent_id = strategy_func(
                agent_id=agent_id,
                user_input=user_input,
                memory_context=memory_context,
                candidates=candidates
            )

            if best_agent_id:
                self.logger.debug(f"Selected agent: {best_agent_id} via {strategy}")
            return best_agent_id

        except Exception as e:
            self.logger.error(f"Routing error: {e}", exc_info=True)
            return None

    def _get_candidate_agents(self, agent_id: str) -> List[str]:
        """
        获取当前 agent 的所有直接子节点（不区分叶子或中间节点）
        如果没有子节点，返回空列表。
        """
        if not self.tree_manager:
            self.logger.error("TreeManager not initialized")
            return []

        try:
            # 直接返回子节点列表（可能为空）
            return self.tree_manager.get_children(agent_id) if agent_id else []
        except Exception as e:
            self.logger.error(f"Error fetching children from TreeManager for agent '{agent_id}': {e}", exc_info=True)
            return []

    # ========== 策略函数签名统一更新 ==========

    def _default_routing_strategy(
        self,
        agent_id: str,
        user_input: str,
        memory_context: Optional[str],
        candidates: List[str]
    ) -> Optional[str]:
        # 简单轮询或首节点
        return candidates[0] if candidates else None

    def _semantic_match_strategy(
        self,
        agent_id: str,
        user_input: str,
        memory_context: Optional[str],
        candidates: List[str]
    ) -> Optional[str]:
        if not candidates:
            return None
        best_score, best_agent = 0.0, None
        for cid in candidates:
            meta = self.registry.get_agent_meta(cid)
            if not meta:
                continue
            score = self._calculate_semantic_score(user_input, meta)
            if score > best_score:
                best_score, best_agent = score, cid
        return best_agent if best_score > 0.2 else candidates[0]


    # ========== 智能策略：融合 user_input + memory_context ==========

    def _qwen_intelligent_strategy(
        self,
        agent_id: str,
        user_input: str,
        memory_context: Optional[str],
        candidates: List[str]
    ) -> Optional[str]:
        if not candidates:
            return None

        # 构建候选节点描述
        actors = []
        for cid in candidates:
            meta = self.tree_manager.get_agent_meta(cid)
            if not meta:
                continue
            actors.append({
                "code": cid,
                "name": meta.get("name", "Unnamed"),
                "capability": meta.get("capability", []),
                "description": meta.get("description", ""),
                "datascope": meta.get("datascope", {})
            })

        if not actors:
            return None

        # 构建提示词
        prompt = self._build_intelligent_prompt(
            user_input=user_input,
            memory_context=memory_context,
            actors=actors
        )

        try:
            response = self._call_qwen(prompt)
            selected_code = self._parse_selected_code(response)
            if selected_code and selected_code in candidates:
                return selected_code
        except Exception as e:
            self.logger.error(f"Qwen intelligent routing failed: {e}")

        # fallback
        return self._default_routing_strategy(agent_id, user_input, memory_context, candidates)

    def _build_intelligent_prompt(
        self,
        user_input: str,
        memory_context: Optional[str],
        actors: List[Dict]
    ) -> str:
        # 格式化记忆上下文
        mem_part = memory_context.strip() if memory_context else "无相关记忆上下文"

        # 格式化候选节点
        actors_desc = "\n".join(
            f"【{a['name']}】\n- 节点代码: {a['code']}\n- 能力: {', '.join(a['capability']) if a['capability'] else '通用'}\n"
            f"- 描述: {a['description']}\n- 数据范围: {a['datascope']}\n"
            for a in actors
        )

        return (
            "你是一个智能任务调度专家，请根据用户当前请求和对话记忆，从可用子节点中选择最合适的一个。\n\n"
            "【用户当前请求】\n"
            f"{user_input}\n\n"
            "【对话与记忆上下文】\n"
            f"{mem_part}\n\n"
            "【可用子节点列表】\n"
            f"{actors_desc}\n\n"
            "请严格只输出一个「节点代码」（例如：analyzer_v3），不要任何解释、标点或额外文字。\n"
            "如果无法确定，请输出 None。"
        )
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
    

    def _parse_selected_actor_name(self, llm_output: str) -> str:
        """从大模型输出中提取节点名称（简单清洗）"""
        return llm_output.strip().split('\n')[0].strip()
    
    def call_qwen(self,prompt: str) -> str:
        from ..llm.interface import ILLMCapability
        from ..registry import capability_registry
        llm = capability_registry.get_capability("llm", ILLMCapability)
        res=llm.generate(prompt)
        return res



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
