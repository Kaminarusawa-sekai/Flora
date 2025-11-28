from abc import abstractmethod
from typing import List, Union, Dict
from ..capability_base import CapabilityBase


class ILLMCapability(CapabilityBase):
    """LLM 能力的标准接口"""
    
    @abstractmethod
    def generate(self, prompt: str, images: List[str] = None) -> str:
        """统一生成接口，支持纯文本或多模态"""
        pass

    @abstractmethod
    def generate_chat(self, messages: List[Dict[str, str]]) -> str:
        """多轮对话接口"""
        pass

    @abstractmethod
    def embedding(self, text: str) -> List[float]:
        """生成向量"""
        pass
    
    def get_capability_type(self) -> str:
        return "llm"