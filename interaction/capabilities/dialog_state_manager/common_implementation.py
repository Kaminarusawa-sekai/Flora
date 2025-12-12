from typing import Dict, Any, Optional, List
from .interface import IDialogStateManager
from ...common import (
    DialogStateDTO,
    TaskDraftDTO,
    TaskSummary
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonDialogStateManager(IDialogStateManager):
    """对话状态管理器 - 维护全局对话状态"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化对话状态管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
    
    def shutdown(self) -> None:
        """关闭对话状态管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "dialog_management"
    
    def get_or_create_dialog_state(self, session_id: str) -> DialogStateDTO:
        """获取或创建对话状态
        
        Args:
            session_id: 会话ID
            
        Returns:
            对话状态DTO
        """
        # 从存储中获取对话状态
        state = self.task_storage.get_dialog_state(session_id)
        
        # 如果不存在，创建新的对话状态
        if not state:
            state = DialogStateDTO(
                session_id=session_id,
                current_intent=None,
                active_task_draft=None,
                active_task_execution=None,
                pending_tasks=[],
                recent_tasks=[],
                last_mentioned_task_id=None,
                is_in_idle_mode=False
            )
            self.task_storage.save_dialog_state(state)
        
        return state
    
    def update_dialog_state(self, state: DialogStateDTO) -> bool:
        """更新对话状态
        
        Args:
            state: 对话状态DTO
            
        Returns:
            是否更新成功
        """
        return self.task_storage.update_dialog_state(state)
    
    def set_active_draft(self, session_id: str, draft: Optional[TaskDraftDTO]) -> DialogStateDTO:
        """设置活跃的任务草稿
        
        Args:
            session_id: 会话ID
            draft: 任务草稿DTO，None表示清除活跃草稿
            
        Returns:
            更新后的对话状态
        """
        state = self.get_or_create_dialog_state(session_id)
        state.active_task_draft = draft
        self.update_dialog_state(state)
        return state
    
    def set_active_execution(self, session_id: str, task_id: Optional[str]) -> DialogStateDTO:
        """设置活跃的任务执行
        
        Args:
            session_id: 会话ID
            task_id: 任务执行ID，None表示清除活跃执行
            
        Returns:
            更新后的对话状态
        """
        state = self.get_or_create_dialog_state(session_id)
        state.active_task_execution = task_id
        self.update_dialog_state(state)
        return state
    
    def add_recent_task(self, session_id: str, task_summary: TaskSummary) -> DialogStateDTO:
        """添加最近任务到对话状态
        
        Args:
            session_id: 会话ID
            task_summary: 任务摘要
            
        Returns:
            更新后的对话状态
        """
        state = self.get_or_create_dialog_state(session_id)
        
        # 限制最近任务的数量
        MAX_RECENT_TASKS = 5
        state.recent_tasks.insert(0, task_summary)
        if len(state.recent_tasks) > MAX_RECENT_TASKS:
            state.recent_tasks = state.recent_tasks[:MAX_RECENT_TASKS]
        
        self.update_dialog_state(state)
        return state
    
    def set_last_mentioned_task(self, session_id: str, task_id: Optional[str]) -> DialogStateDTO:
        """设置最后提及的任务
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        state = self.get_or_create_dialog_state(session_id)
        state.last_mentioned_task_id = task_id
        self.update_dialog_state(state)
        return state
    
    def get_last_mentioned_task(self, session_id: str) -> Optional[str]:
        """获取最后提及的任务
        
        Args:
            session_id: 会话ID
            
        Returns:
            最后提及的任务ID
        """
        state = self.get_or_create_dialog_state(session_id)
        return state.last_mentioned_task_id
    
    def add_pending_task(self, session_id: str, task_id: str) -> DialogStateDTO:
        """添加待处理任务到任务栈
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        state = self.get_or_create_dialog_state(session_id)
        if task_id not in state.pending_tasks:
            state.pending_tasks.append(task_id)
            self.update_dialog_state(state)
        return state
    
    def remove_pending_task(self, session_id: str, task_id: str) -> DialogStateDTO:
        """从任务栈中移除待处理任务
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        state = self.get_or_create_dialog_state(session_id)
        if task_id in state.pending_tasks:
            state.pending_tasks.remove(task_id)
            self.update_dialog_state(state)
        return state