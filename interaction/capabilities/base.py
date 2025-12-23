from typing import Any, Optional, Dict, List
from abc import ABC, abstractmethod
from .capability_base import CapabilityBase
from common import (
    UserInputDTO,
    IntentRecognitionResultDTO,
    DialogStateDTO,
    TaskDraftDTO,
    TaskExecutionContextDTO,
    SystemResponseDTO,
    ExecutionStatus
)

class BaseManager(CapabilityBase):
    """所有管理器的基类"""
    def __init__(self, context: Dict[str, Any] = None):
        self.context = context or {}
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化管理器"""
        pass
    
    @abstractmethod
    def shutdown(self) -> None:
        """关闭管理器"""
        pass
    
    @abstractmethod
    def get_capability_type(self) -> str:
        """返回能力类型"""
        pass

class TaskStorage(ABC):
    """任务存储接口，负责与数据库交互"""
    
    @abstractmethod
    def save_draft(self, draft: TaskDraftDTO) -> str:
        """保存任务草稿"""
        pass
    
    @abstractmethod
    def get_draft(self, draft_id: str) -> Optional[TaskDraftDTO]:
        """获取任务草稿"""
        pass
    
    @abstractmethod
    def update_draft(self, draft: TaskDraftDTO) -> bool:
        """更新任务草稿"""
        pass
    
    @abstractmethod
    def delete_draft(self, draft_id: str) -> bool:
        """删除任务草稿"""
        pass
    
    @abstractmethod
    def list_drafts(self, user_id: str) -> List[TaskDraftDTO]:
        """列出用户的所有任务草稿"""
        pass
    
    @abstractmethod
    def save_execution_context(self, context: TaskExecutionContextDTO) -> str:
        """保存任务执行上下文"""
        pass
    
    @abstractmethod
    def get_execution_context(self, task_id: str) -> Optional[TaskExecutionContextDTO]:
        """获取任务执行上下文"""
        pass
    
    @abstractmethod
    def update_execution_context(self, context: TaskExecutionContextDTO) -> bool:
        """更新任务执行上下文"""
        pass
    
    @abstractmethod
    def list_execution_contexts(self, user_id: str, filters: Dict[str, Any] = None) -> List[TaskExecutionContextDTO]:
        """列出用户的任务执行上下文"""
        pass
    
    @abstractmethod
    def save_dialog_state(self, state: DialogStateDTO) -> str:
        """保存对话状态"""
        pass
    
    @abstractmethod
    def get_dialog_state(self, session_id: str) -> Optional[DialogStateDTO]:
        """获取对话状态"""
        pass
    
    @abstractmethod
    def update_dialog_state(self, state: DialogStateDTO) -> bool:
        """更新对话状态"""
        pass

class MockTaskStorage(TaskStorage):
    """模拟的任务存储实现，用于开发和测试"""
    def __init__(self):
        self.drafts: Dict[str, TaskDraftDTO] = {}
        self.execution_contexts: Dict[str, TaskExecutionContextDTO] = {}
        self.dialog_states: Dict[str, DialogStateDTO] = {}
    
    def save_draft(self, draft: TaskDraftDTO) -> str:
        self.drafts[draft.draft_id] = draft
        return draft.draft_id
    
    def get_draft(self, draft_id: str) -> Optional[TaskDraftDTO]:
        return self.drafts.get(draft_id)
    
    def update_draft(self, draft: TaskDraftDTO) -> bool:
        if draft.draft_id in self.drafts:
            self.drafts[draft.draft_id] = draft
            return True
        return False
    
    def delete_draft(self, draft_id: str) -> bool:
        if draft_id in self.drafts:
            del self.drafts[draft_id]
            return True
        return False
    
    def list_drafts(self, user_id: str) -> List[TaskDraftDTO]:
        # 这里简化实现，实际应该按用户ID过滤
        return list(self.drafts.values())
    
    def save_execution_context(self, context: TaskExecutionContextDTO) -> str:
        self.execution_contexts[context.task_id] = context
        return context.task_id
    
    def get_execution_context(self, task_id: str) -> Optional[TaskExecutionContextDTO]:
        return self.execution_contexts.get(task_id)
    
    def update_execution_context(self, context: TaskExecutionContextDTO) -> bool:
        if context.task_id in self.execution_contexts:
            self.execution_contexts[context.task_id] = context
            return True
        return False
    
    def list_execution_contexts(self, user_id: str, filters: Dict[str, Any] = None) -> List[TaskExecutionContextDTO]:
        # 这里简化实现，实际应该按用户ID和过滤条件过滤
        return list(self.execution_contexts.values())
    
    def save_dialog_state(self, state: DialogStateDTO) -> str:
        self.dialog_states[state.session_id] = state
        return state.session_id
    
    def get_dialog_state(self, session_id: str) -> Optional[DialogStateDTO]:
        return self.dialog_states.get(session_id)
    
    def update_dialog_state(self, state: DialogStateDTO) -> bool:
        if state.session_id in self.dialog_states:
            self.dialog_states[state.session_id] = state
            return True
        return False