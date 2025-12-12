from typing import Dict, Any, Optional
from .interface import IUserInputManager
from ...common import UserInputDTO
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonUserInputManager(IUserInputManager):
    """用户输入管理器 - 接收并解析用户的原始输入"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化用户输入管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
    
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
        # 1. 解析用户输入
        processed_data = {
            "session_id": user_input.session_id,
            "user_id": user_input.user_id,
            "utterance": user_input.utterance,
            "timestamp": user_input.timestamp,
            "metadata": user_input.metadata,
        }
        
        # 2. 使用LLM增强输入处理
        prompt = f"优化用户输入的表达，使其更清晰、更易于后续处理：\n\n用户输入：{user_input.utterance}"
        enhanced_utterance = self.llm.generate(prompt)
        processed_data["enhanced_utterance"] = enhanced_utterance
        
        # 3. 会话管理和上下文跟踪
        # 这里可以添加会话超时检查、用户认证等逻辑
        
        # 4. 返回处理后的数据
        return processed_data