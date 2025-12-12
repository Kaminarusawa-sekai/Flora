from typing import Dict, Any, Optional, List
from .interface import IIntentRecognitionManager
from ...common import (
    IntentRecognitionResultDTO,
    IntentType,
    EntityDTO,
    UserInputDTO
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonIntentRecognitionManager(IIntentRecognitionManager):
    """意图识别管理器 - 分析用户输入，确定意图和实体"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化意图识别管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
    
    def shutdown(self) -> None:
        """关闭意图识别管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "nlu"
    
    def recognize_intent(self, user_input: UserInputDTO) -> IntentRecognitionResultDTO:
        """识别用户意图
        
        Args:
            user_input: 处理后的用户输入
            
        Returns:
            意图识别结果DTO
        """
        utterance = user_input.utterance
        
        # 使用LLM增强意图识别
        prompt = f"请分析以下用户输入，识别出用户的意图类型和相关实体：\n\n用户输入：{utterance}\n\n意图类型只能是以下之一：CREATE_TASK, MODIFY_TASK, QUERY_TASK, DELETE_TASK, IDLE_CHAT, RESUME_INTERRUPTED, CANCEL_TASK, PAUSE_TASK, RESUME_TASK, RETRY_TASK, SET_SCHEDULE\n\n请以JSON格式返回，包含intent（意图类型）、confidence（置信度0-1）、entities（实体列表，每个实体包含name、value、resolved_value）。"
        
        llm_result = self.llm.generate(prompt)
        
        # 基础意图识别（作为LLM的备选方案）
        intent = IntentType.IDLE
        confidence = 0.5
        entities = []
        
        # 基于关键词匹配的简化意图识别
        lower_utterance = utterance.lower()
        if any(keyword in lower_utterance for keyword in ["创建", "新建", "添加"]):
            intent = IntentType.CREATE
            confidence = 0.9
        elif any(keyword in lower_utterance for keyword in ["修改", "编辑", "更新"]):
            intent = IntentType.MODIFY
            confidence = 0.8
        elif any(keyword in lower_utterance for keyword in ["查询", "查看", "列表", "有哪些"]):
            intent = IntentType.QUERY
            confidence = 0.9
        elif any(keyword in lower_utterance for keyword in ["删除", "取消"]):
            intent = IntentType.DELETE
            confidence = 0.8
        elif any(keyword in lower_utterance for keyword in ["恢复", "继续"]):
            intent = IntentType.RESUME
            confidence = 0.7
        elif any(keyword in lower_utterance for keyword in ["暂停"]):
            intent = IntentType.PAUSE
            confidence = 0.8
        elif any(keyword in lower_utterance for keyword in ["重试"]):
            intent = IntentType.RETRY
            confidence = 0.8
        elif any(keyword in lower_utterance for keyword in ["定时", "每天", "每周", "每小时"]):
            intent = IntentType.SET_SCHEDULE
            confidence = 0.8
        
        # 使用LLM增强实体提取
        entities = self._extract_entities(utterance)
        
        return IntentRecognitionResultDTO(
            intent=intent,
            confidence=confidence,
            entities=entities,
            raw_nlu_output={"original_utterance": user_input.utterance, "llm_analysis": llm_result}
        )
    
    def _extract_entities(self, utterance: str) -> List[EntityDTO]:
        """提取实体信息
        
        Args:
            utterance: 用户输入文本
            
        Returns:
            实体列表
        """
        # 使用LLM增强实体提取
        prompt = f"请从以下用户输入中提取实体信息：\n\n用户输入：{utterance}\n\n请以JSON格式返回实体列表，每个实体包含name（实体名称）、value（原始值）、resolved_value（解析后的值）。"
        
        llm_result = self.llm.generate(prompt)
        
        # 基础实体提取（作为LLM的备选方案）
        entities = []
        
        # 简化的实体提取逻辑，实际应该解析LLM返回的JSON
        # 这里可以添加更多的实体提取逻辑
        
        return entities