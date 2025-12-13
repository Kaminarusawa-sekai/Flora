from typing import Dict, Any, Optional
from .interface import IUserInputManagerCapability
from ...common import UserInputDTO
from interaction.capabilities.registry import capability_registry
from interaction.capabilities.llm.interface import ILLMCapability
from interaction.capabilities.memory.interface import IMemoryService
from interaction.capabilities.context_manager.interface import IContextManagerCapability

class CommonUserInput(IUserInputManagerCapability):
    """用户输入管理器 - 接收并解析用户的原始输入"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化用户输入管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = capability_registry.get_capability("llm", ILLMCapability)
        # 获取内存服务
        self.memory = capability_registry.get_capability("memory", IMemoryService)
        # 获取对话历史存储
        self.history_store = capability_registry.get_capability("context_manager", IContextManagerCapability)
        # 上下文窗口大小
        self.context_window = config.get("context_window", 5)
    
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
        # 注意：我们的上下文管理器get_recent_turns方法返回的是DialogTurn对象列表
        # 我们需要转换为方案中期望的格式
        recent_turns = self.history_store.get_recent_turns(limit=self.context_window)
        dialog_history = [
            {"role": turn.role, "utterance": turn.utterance}
            for turn in recent_turns
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
        llm_result = self.llm.generate(prompt)
        import json
        try:
            parsed_result = json.loads(llm_result)
        except json.JSONDecodeError:
            # 如果LLM返回的不是有效的JSON，使用默认值
            parsed_result = {
                "enhanced_utterance": user_input.utterance,
                "resolved_references": {},
                "implied_action": "",
                "target_entity": "",
                "new_time": ""
            }
        
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
        
        return enriched_input