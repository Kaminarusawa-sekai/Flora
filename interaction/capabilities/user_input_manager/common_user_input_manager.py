from typing import Dict, Any, Optional
from .interface import IUserInputManagerCapability
from common import UserInputDTO,DialogTurn
from capabilities.registry import capability_registry
from capabilities.llm.interface import ILLMCapability
from capabilities.memory.interface import IMemoryCapability
import logging
logger = logging.getLogger(__name__)

class CommonUserInput(IUserInputManagerCapability):
    """用户输入管理器 - 接收并解析用户的原始输入"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化用户输入管理器"""
        self.config = config
        self._llm = None
        self._memory = None
        self._history_store = None
        # 上下文窗口大小
        self.context_window = config.get("context_window", 5)
        
    @property
    def llm(self):
        """懒加载LLM能力"""
        if self._llm is None:
            self._llm = capability_registry.get_capability("llm", ILLMCapability)
        return self._llm
        
    @property
    def memory(self):
        """懒加载内存服务"""
        if self._memory is None:
            self._memory = capability_registry.get_capability("memory", IMemoryCapability)
        return self._memory
        
    @property
    def history_store(self):
        """懒加载对话历史存储"""
        from capabilities.context_manager.interface import IContextManagerCapability
        if self._history_store is None:
            self._history_store = capability_registry.get_capability("context_manager", IContextManagerCapability)
        return self._history_store
    
    def shutdown(self) -> None:
        """关闭用户输入管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "input_processing"
    
    def process_input(self, user_input: UserInputDTO) -> Dict[str, Any]:
        """处理用户输入
        
        Args:
            user_input: 用户输入DTO
            
        Returns:
            处理后的输入数据，包含会话信息
        """
        # 1. 读取会话历史
        # 注意：我们的上下文管理器get_turns_by_session方法返回的是DialogTurn对象列表
        # 我们需要转换为方案中期望的格式
        recent_turns = self.history_store.get_turns_by_session(session_id=user_input.session_id, limit=self.context_window)
        

        dialog_history = [
            {"role": turn.role, "utterance": turn.utterance}
            for turn in  reversed(recent_turns)
        ]
        
        # 2. 检索长期记忆
        memories = self.memory.search_memories(
            user_id=user_input.user_id,
            query=user_input.utterance,
            limit=3
        )
        
        # 3. 构造LLM Prompt
        prompt = f"""【对话历史】
{"\n".join([f"{turn['role']}：{turn['utterance']}" for turn in dialog_history])}

【长期记忆】
{memories}

【当前输入】
{user_input.utterance}

请输出 JSON：
{{
"enhanced_utterance": "",
"resolved_references": {{}},
"implied_action": "",
"target_entity": "",
"new_time": ""
}}"""
        
        # 4. 调用LLM，解析结果
        logger.info(f"LLM Prompt: {prompt}")
        llm_result = self.llm.generate(prompt, parse_json=True)
        parsed_result = llm_result
        # import json
        # try:
        #     parsed_result = json.loads(llm_result)
        # except json.JSONDecodeError:
        #     # 如果LLM返回的不是有效的JSON，使用默认值
        #     parsed_result = {
        #         "enhanced_utterance": user_input.utterance,
        #         "resolved_references": {},
        #         "implied_action": "",
        #         "target_entity": "",
        #         "new_time": ""
        #     }
        
        # 5. 构造返回数据
        enriched_input = {
            "session_id": user_input.session_id,
            "user_id": user_input.user_id,
            "utterance": user_input.utterance,
            "enhanced_utterance": parsed_result["enhanced_utterance"],
            "resolved_references": parsed_result["resolved_references"],
            "implied_action": parsed_result["implied_action"],
            "target_entity": parsed_result["target_entity"],
            "new_time": parsed_result["new_time"],
            "dialog_history": dialog_history,
            "long_term_memories": memories,
            "timestamp": user_input.timestamp,
            "metadata": user_input.metadata
        }
        self.history_store.add_turn(DialogTurn(role="user", utterance=user_input.utterance, enhanced_utterance=parsed_result["enhanced_utterance"], timestamp=user_input.timestamp, session_id=user_input.session_id, user_id=user_input.user_id))
        return enriched_input