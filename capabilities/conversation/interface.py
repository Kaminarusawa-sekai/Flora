"""对话管理能力接口定义"""
from typing import Dict, Optional, Any, List, Tuple
from abc import ABC, abstractmethod
from capabilities.capability_base import CapabilityBase
from common.types.draft import TaskDraft


class IConversationManagerCapability(CapabilityBase):
    """对话管理能力接口"""

    @abstractmethod
    def process_user_input(self, user_input: str, user_id: str = "default_user") -> str:
        """Process user input with draft management"""
        raise NotImplementedError

    @abstractmethod
    def handle_user_input(self, user_input: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        前台入口：处理用户输入并返回完整的处理结果

        Returns:
            Dict containing:
            - action: str ("continue_task", "new_task", "parameter_completion", "clarification", "chat")
            - task_id: Optional[str] (如果是参数补充或继续任务)
            - parameters: Dict[str, Any] (补充的参数)
            - message: str (返回给用户的消息)
            - needs_backend: bool (是否需要转发给后台AgentActor)
            - intent: IntentType (用户意图类型)
        """
        raise NotImplementedError

    @abstractmethod
    def is_parameter_completion(self, user_input: str, user_id: str = "default_user") -> bool:
        """判断用户输入是否是参数补充"""
        raise NotImplementedError

    @abstractmethod
    def identify_target_task(self, user_input: str, user_id: str = "default_user") -> Optional[str]:
        """识别用户正在补充哪个任务的参数，返回task_id"""
        raise NotImplementedError

    @abstractmethod
    def pause_task_for_parameters(self, task_id: str, missing_params: List[str],
                                  task_context: Dict[str, Any], user_id: str = "default_user") -> str:
        """
        后台调用：暂停任务链，等待用户补充参数

        Args:
            task_id: 任务ID
            missing_params: 缺失的参数列表
            task_context: 任务上下文（包含已有信息）
            user_id: 用户ID

        Returns:
            向用户询问参数的问题
        """
        raise NotImplementedError

    @abstractmethod
    def get_pending_tasks(self, user_id: str = "default_user") -> List[TaskDraft]:
        """获取用户所有等待参数补充的任务"""
        raise NotImplementedError

    @abstractmethod
    def complete_task_parameters(self, task_id: str, user_input: str,
                                 user_id: str = "default_user") -> Tuple[bool, Dict[str, Any]]:
        """
        补充任务参数

        Returns:
            Tuple[is_complete, parameters]:
            - is_complete: 参数是否已全部补充完成
            - parameters: 已补充的参数字典
        """
        raise NotImplementedError

    @abstractmethod
    def is_continue_request(self, user_input: str) -> bool:
        """Check if user wants to continue draft"""
        raise NotImplementedError

    @abstractmethod
    def restore_latest_draft(self, user_id: str = "default_user") -> bool:
        """Restore latest draft"""
        raise NotImplementedError

    @abstractmethod
    def save_draft(self, draft: TaskDraft, user_id: str = "default_user"):
        """Save current draft"""
        raise NotImplementedError

    @abstractmethod
    def clear_draft(self):
        """Clear current draft"""
        raise NotImplementedError
