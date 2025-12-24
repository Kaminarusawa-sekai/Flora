from typing import List
from abc import abstractmethod
from ..base import BaseManager
from common import (
    IntentRecognitionResultDTO,
    UserInputDTO,
    EntityDTO,
    DialogStateDTO
)

class IIntentRecognitionManagerCapability(BaseManager):
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
    
    @abstractmethod
    def judge_special_intent(self, user_input: str, dialog_state: DialogStateDTO) -> str:
        """判断特殊意图：确认、修改草稿或拒绝
        
        Args:
            user_input: 用户输入文本
            dialog_state: 对话状态DTO
            
        Returns:
            字符串表示的意图类型："CONFIRM"、"CANCEL"、"MODIFY" 或空字符串
        """
        pass