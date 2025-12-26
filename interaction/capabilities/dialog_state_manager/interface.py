from typing import List, Optional, Any, Dict
from abc import abstractmethod
from ..base import BaseManager, TaskStorage
from common import (
    DialogStateDTO,
    TaskDraftDTO,
    TaskSummary,
    IntentRecognitionResultDTO,
    UserInputDTO
)

class IDialogStateManagerCapability(BaseManager):
    """对话状态管理器接口"""
    
    def __init__(self):
        super().__init__()
    
    @abstractmethod
    def get_or_create_dialog_state(self, session_id: str, user_id: str) -> DialogStateDTO:
        """获取或创建对话状态
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            对话状态DTO
        """
        pass
    
    @abstractmethod
    def update_dialog_state(self, state: DialogStateDTO) -> bool:
        """更新对话状态
        
        Args:
            state: 对话状态DTO
            
        Returns:
            是否更新成功
        """
        pass
    
    @abstractmethod
    def set_active_draft(self, session_id: str, draft: Optional[TaskDraftDTO]) -> DialogStateDTO:
        """设置活跃的任务草稿
        
        Args:
            session_id: 会话ID
            draft: 任务草稿DTO，None表示清除活跃草稿
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def set_active_execution(self, session_id: str, task_id: Optional[str]) -> DialogStateDTO:
        """设置活跃的任务执行
        
        Args:
            session_id: 会话ID
            task_id: 任务执行ID，None表示清除活跃执行
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def add_recent_task(self, session_id: str, task_summary: TaskSummary) -> DialogStateDTO:
        """添加最近任务到对话状态
        
        Args:
            session_id: 会话ID
            task_summary: 任务摘要
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def set_last_mentioned_task(self, session_id: str, task_id: Optional[str]) -> DialogStateDTO:
        """设置最后提及的任务
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def get_last_mentioned_task(self, session_id: str) -> Optional[str]:
        """获取最后提及的任务
        
        Args:
            session_id: 会话ID
            
        Returns:
            最后提及的任务ID
        """
        pass
    
    @abstractmethod
    def add_pending_task(self, session_id: str, task_id: str) -> DialogStateDTO:
        """添加待处理任务到任务栈
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def remove_pending_task(self, session_id: str, task_id: str) -> DialogStateDTO:
        """从任务栈中移除待处理任务
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def process_intent_result(
        self,
        session_id: str,
        intent_result: IntentRecognitionResultDTO,
        user_input: Optional[UserInputDTO] = None
    ) -> DialogStateDTO:
        """主入口：根据意图识别结果更新对话状态，可能触发澄清、草稿填充、意图修正等
        
        Args:
            session_id: 会话ID
            intent_result: 意图识别结果
            user_input: 用户输入（可选，用于日志或澄清）
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def cleanup_expired_sessions(self, max_idle_minutes: int = 30) -> int:
        """清理超过 N 分钟未活动的会话
        
        Args:
            max_idle_minutes: 最大空闲分钟数
            
        Returns:
            清理的会话数量
        """
        pass
    
    @abstractmethod
    def set_waiting_for_confirmation(self, dialog_state: DialogStateDTO, action: str, payload: dict) -> DialogStateDTO:
        """设置等待确认状态
        
        Args:
            dialog_state: 对话状态DTO
            action: 等待确认的动作类型
            payload: 确认所需的上下文数据
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def clear_waiting_for_confirmation(self, dialog_state: DialogStateDTO) -> DialogStateDTO:
        """清除等待确认状态
        
        Args:
            dialog_state: 对话状态DTO
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def clear_active_draft(self, dialog_state: DialogStateDTO) -> DialogStateDTO:
        """清除活跃的任务草稿
        
        Args:
            dialog_state: 对话状态DTO
            
        Returns:
            更新后的对话状态
        """
        pass
    
    @abstractmethod
    def generate_session_name(self, session_id: str, user_input: str) -> Dict[str, str]:
        """生成会话名称和描述
        
        Args:
            session_id: 会话ID
            user_input: 用户输入
            
        Returns:
            包含name和description的字典
        """
        pass
    
    @abstractmethod
    def update_dialog_state_fields(self, dialog_state: DialogStateDTO, **kwargs) -> DialogStateDTO:
        """更新对话状态的多个字段
        
        Args:
            dialog_state: 对话状态DTO
            **kwargs: 要更新的字段名和值，只允许更新DialogStateDTO中存在的字段
            
        Returns:
            更新后的对话状态DTO
        """
        pass