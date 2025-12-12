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
    intent: IntentType
    confidence: float
    entities: List[EntityDTO] = []
    raw_nlu_output: Dict[str, Any] = Field(default_factory=dict) # 调试用