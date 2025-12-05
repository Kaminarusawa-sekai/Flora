from typing import Dict, Any, List, Optional
from ..capability_base import CapabilityBase


class IDimensionParserCapability(CapabilityBase):
    """LLM维度解析能力接口"""
    
    def get_capability_type(self) -> str:
        """获取能力类型"""
        raise NotImplementedError
    
    def discover_schema(self) -> Dict[str, Any]:
        """
        步骤1: 让LLM自行决定优化哪些维度
        
        Returns:
            dict: 包含维度信息和初始向量的字典
        """
        raise NotImplementedError
    
    def vector_to_instruction(self, vector: List[float], context: Optional[Dict[str, Any]] = None) -> str:
        """
        步骤2: 隐向量 → 自然语言指令
        
        Args:
            vector: 隐向量
            context: 上下文信息（可选）
            
        Returns:
            str: 自然语言指令
        """
        raise NotImplementedError
    
    def output_to_score(self, raw_output: str) -> Dict[str, Any]:
        """
        步骤3: 原始输出 → 分数 + 结构化反馈
        
        Args:
            raw_output: 执行输出内容
            
        Returns:
            Dict[str, Any]: 包含评分和反馈的字典
        """
        raise NotImplementedError
    
    def set_last_instruction(self, instruction: str) -> None:
        """
        设置上一次的指令，用于历史记录
        
        Args:
            instruction: 上一次的指令
        """
        raise NotImplementedError
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取历史记录
        
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        raise NotImplementedError
