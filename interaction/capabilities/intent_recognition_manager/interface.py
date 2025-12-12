from typing import List
from abc import abstractmethod
from ..base import BaseManager
from ...common import (
    IntentRecognitionResultDTO,
    UserInputDTO,
    EntityDTO
)

class IIntentRecognitionManager(BaseManager):
    """意图识别管理器接口"""
    
    @abstractmethod
    def recognize_intent(self, user_input: UserInputDTO) -> IntentRecognitionResultDTO:
        """识别用户意图
        
        Args:
            user_input: 处理后的用户输入
            
        Returns:
            意图识别结果DTO
        """
        pass
    
    @abstractmethod
    def _extract_entities(self, utterance: str) -> List[EntityDTO]:
        """提取实体信息
        
        Args:
            utterance: 用户输入文本
            
        Returns:
            实体列表
        """
        pass