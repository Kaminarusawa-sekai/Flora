from abc import abstractmethod
from typing import List, Union, Dict, Any, Optional
from ..capability_base import CapabilityBase


class ILLMCapability(CapabilityBase):
    """LLM 能力的标准接口"""
    
    @abstractmethod
    def generate( self,
        prompt: str,
        images: Optional[List[str]] = None,
        parse_json: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        **kwargs) ->  Union[str, Dict[str, Any], None]:
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