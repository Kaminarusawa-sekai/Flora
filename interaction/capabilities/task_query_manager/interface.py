from typing import Dict, Any, Optional
from abc import abstractmethod
from ..base import BaseManager, TaskStorage
from common import (
    IntentRecognitionResultDTO,
    TaskExecutionContextDTO
)

class ITaskQueryManagerCapability(BaseManager):
    """任务查询管理器接口"""
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def process_query_intent(self, intent_result: IntentRecognitionResultDTO, user_id: str, last_mentioned_task_id: Optional[str] = None) -> Dict[str, Any]:
        """处理查询意图，返回匹配的任务列表
        
        Args:
            intent_result: 意图识别结果DTO
            user_id: 用户ID
            last_mentioned_task_id: 最后提及的任务ID（用于指代消解）
            
        Returns:
            结构化的任务查询结果，可直接用于SystemResponseDTO.displayData
        """
        pass