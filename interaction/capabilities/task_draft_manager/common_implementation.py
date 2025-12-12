from typing import Dict, Any, Optional, List
from .interface import ITaskDraftManager
from ...common import (
    TaskDraftDTO,
    SlotValueDTO,
    ScheduleDTO,
    SlotSource,
    IntentRecognitionResultDTO
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonTaskDraftManager(ITaskDraftManager):
    """任务草稿管理器 - 维护未完成的任务草稿，管理多轮填槽过程"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务草稿管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
    
    def shutdown(self) -> None:
        """关闭任务草稿管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "task_draft"
    
    def create_draft(self, task_type: str, session_id: str, user_id: str) -> TaskDraftDTO:
        """创建新的任务草稿
        
        Args:
            task_type: 任务类型
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            任务草稿DTO
        """
        draft = TaskDraftDTO(
            task_type=task_type,
            status="DRAFT",
            slots={},
            missing_slots=[],
            invalid_slots=[],
            schedule=None,
            is_cancelable=True,
            is_resumable=True,
            original_utterances=[],
        )
        
        # 保存到存储
        self.task_storage.save_draft(draft)
        return draft
    
    def update_draft(self, draft: TaskDraftDTO) -> bool:
        """更新任务草稿
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            是否更新成功
        """
        return self.task_storage.update_draft(draft)
    
    def get_draft(self, draft_id: str) -> Optional[TaskDraftDTO]:
        """获取任务草稿
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            任务草稿DTO，不存在返回None
        """
        return self.task_storage.get_draft(draft_id)
    
    def delete_draft(self, draft_id: str) -> bool:
        """删除任务草稿
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            是否删除成功
        """
        return self.task_storage.delete_draft(draft_id)
    
    def add_utterance_to_draft(self, draft: TaskDraftDTO, utterance: str) -> TaskDraftDTO:
        """添加用户输入到草稿的历史记录
        
        Args:
            draft: 任务草稿DTO
            utterance: 用户输入
            
        Returns:
            更新后的任务草稿
        """
        if utterance not in draft.original_utterances:
            draft.original_utterances.append(utterance)
        return draft
    
    def update_slot(self, draft: TaskDraftDTO, slot_name: str, slot_value: SlotValueDTO) -> TaskDraftDTO:
        """更新草稿的槽位值
        
        Args:
            draft: 任务草稿DTO
            slot_name: 槽位名称
            slot_value: 槽位值DTO
            
        Returns:
            更新后的任务草稿
        """
        draft.slots[slot_name] = slot_value
        return draft
    
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
        # 这里假设实体名称与槽位名称一致，实际可能需要映射
        slot_value = SlotValueDTO(
            raw=str(entity_value),
            resolved=entity_value,
            confirmed=False,
            source=source
        )
        return self.update_slot(draft, entity_name, slot_value)
    
    def validate_draft(self, draft: TaskDraftDTO) -> TaskDraftDTO:
        """验证任务草稿，检查必填槽位和格式
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            更新后的任务草稿，包含缺失和无效的槽位
        """
        # 这里简化实现，实际应该根据任务类型验证必填槽位和格式
        draft.missing_slots = []
        draft.invalid_slots = []
        
        # 示例：假设所有任务都需要"task_name"槽位
        if "task_name" not in draft.slots:
            draft.missing_slots.append("task_name")
        
        return draft
    
    def prepare_for_execution(self, draft: TaskDraftDTO) -> Dict[str, Any]:
        """准备任务执行所需的所有参数
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            执行参数字典
        """
        # 从草稿的槽位中提取已确认的解析值
        parameters = {}
        for slot_name, slot_value in draft.slots.items():
            parameters[slot_name] = slot_value.resolved
        
        return parameters
    
    def set_schedule(self, draft: TaskDraftDTO, schedule: ScheduleDTO) -> TaskDraftDTO:
        """设置任务的调度信息
        
        Args:
            draft: 任务草稿DTO
            schedule: 调度信息DTO
            
        Returns:
            更新后的任务草稿
        """
        draft.schedule = schedule
        return draft
    
    def update_draft_from_intent(self, draft: TaskDraftDTO, intent_result: IntentRecognitionResultDTO) -> TaskDraftDTO:
        """根据意图识别结果更新任务草稿
        
        Args:
            draft: 任务草稿DTO
            intent_result: 意图识别结果DTO
            
        Returns:
            更新后的任务草稿
        """
        # 将识别到的实体填充到槽位
        for entity in intent_result.entities:
            draft = self.fill_entity_to_slot(
                draft, entity.name, entity.resolved_value or entity.value, SlotSource.INFERENCE)