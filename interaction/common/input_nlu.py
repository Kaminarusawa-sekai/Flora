from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from .base import IntentType, SlotSource

class UserInputDTO(BaseModel):
    """📦 [1. UserInputDTO] 用户原始输入"""
    session_id: str
    user_id: str
    utterance: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = Field(default_factory=dict) # 设备信息、渠道等

class EntityDTO(BaseModel):
    """实体/槽位基础单元"""
    name: str
    value: Any              # 提取值
    resolved_value: Any = None  # 标准化值 (如: "明天" -> "2025-10-01")
    confidence: float = 1.0

class IntentRecognitionResultDTO(BaseModel):
    """🎯 [2. IntentRecognitionResultDTO] 意图识别结果"""
    # 主意图字段
    primary_intent: IntentType
    confidence: float
    
    # 候选意图列表 (intent, score)
    alternative_intents: List[tuple[IntentType, float]] = []
    
    # 提取的实体
    entities: List[EntityDTO] = []
    
    # 是否存在显著歧义（如 top2 意图分差 < 0.2）
    is_ambiguous: bool = False
    
    # 调试用
    raw_nlu_output: Dict[str, Any] = Field(default_factory=dict)
    
    # 兼容旧版字段，保持向后兼容
    @property
    def intent(self) -> IntentType:
        """兼容旧版代码，返回主意图"""
        return self.primary_intent