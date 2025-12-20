from typing import Dict, Any, Optional, List
from abc import abstractmethod
from ..base import BaseManager, TaskStorage
from ...common import (
    TaskDraftDTO,
    SlotValueDTO,
    ScheduleDTO,
    SlotSource,
    IntentRecognitionResultDTO
)

class ITaskDraftManagerCapability(BaseManager):
    """任务草稿管理器接口"""
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def create_draft(self, task_type: str, session_id: str, user_id: str) -> TaskDraftDTO:
        """创建新的任务草稿
        
        Args:
            task_type: 任务类型
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            任务草稿DTO
        """
        pass
    
    @abstractmethod
    def update_draft(self, draft: TaskDraftDTO) -> bool:
        """更新任务草稿
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            是否更新成功
        """
        pass
    
    @abstractmethod
    def get_draft(self, draft_id: str) -> Optional[TaskDraftDTO]:
        """获取任务草稿
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            任务草稿DTO，不存在返回None
        """
        pass
    
    @abstractmethod
    def delete_draft(self, draft_id: str) -> bool:
        """删除任务草稿
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    def add_utterance_to_draft(self, draft: TaskDraftDTO, utterance: str) -> TaskDraftDTO:
        """添加用户输入到草稿的历史记录
        
        Args:
            draft: 任务草稿DTO
            utterance: 用户输入
            
        Returns:
            更新后的任务草稿
        """
        pass
    
    @abstractmethod
    def update_slot(self, draft: TaskDraftDTO, slot_name: str, slot_value: SlotValueDTO) -> TaskDraftDTO:
        """更新草稿的槽位值
        
        Args:
            draft: 任务草稿DTO
            slot_name: 槽位名称
            slot_value: 槽位值DTO
            
        Returns:
            更新后的任务草稿
        """
        pass
    
    @abstractmethod
    def fill_entity_to_slot(self, draft: TaskDraftDTO, entity_name: str, entity_value: Any, source: SlotSource) -> TaskDraftDTO:
        """将实体填充到对应的槽位
        
        Args:
            draft: 任务草稿DTO
            entity_name: 实体名称
            entity_value: 实体值
            source: 槽位来源
            
        Returns:
            更新后的任务草稿
        """
        pass
    
    @abstractmethod
    def validate_draft(self, draft: TaskDraftDTO) -> TaskDraftDTO:
        """验证任务草稿，检查必填槽位和格式
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            更新后的任务草稿，包含缺失和无效的槽位
        """
        pass
    
    @abstractmethod
    def prepare_for_execution(self, draft: TaskDraftDTO) -> Dict[str, Any]:
        """准备任务执行所需的所有参数
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            执行参数字典
        """
        pass
    
    @abstractmethod
    def set_schedule(self, draft: TaskDraftDTO, schedule: ScheduleDTO) -> TaskDraftDTO:
        """设置任务的调度信息
        
        Args:
            draft: 任务草稿DTO
            schedule: 调度信息DTO
            
        Returns:
            更新后的任务草稿
        """
        pass
    
    @abstractmethod
    def update_draft_from_intent(self, draft: TaskDraftDTO, intent_result: IntentRecognitionResultDTO) -> TaskDraftDTO:
        """根据意图识别结果更新任务草稿
        
        Args:
            draft: 任务草稿DTO
            intent_result: 意图识别结果DTO
            
        Returns:
            更新后的任务草稿
        """
        pass