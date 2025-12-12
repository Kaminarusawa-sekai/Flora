"""对话管理能力接口定义"""
from typing import Dict, Optional, Any, List, Tuple
from abc import ABC, abstractmethod
from capabilities.capability_base import CapabilityBase
from common.types.draft import TaskDraft
from interaction.common.models import Draft, TaskSpec, ClarificationRequest


class IConversationManagerCapability(CapabilityBase):
    """对话管理能力接口"""

    @abstractmethod
    def process_user_input(self, user_input: str, user_id: str = "default_user") -> str:
        """Process user input with draft management"""
        raise NotImplementedError

    @abstractmethod
    def handle_user_input(self, user_input: str, session_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        前台入口：处理用户输入并返回完整的处理结果

        Args:
            user_input: 用户输入文本
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            Dict containing:
            - action: str ("continue_task", "new_task", "parameter_completion", "clarification", "chat")
            - task_id: Optional[str] (如果是参数补充或继续任务)
            - parameters: Dict[str, Any] (补充的参数)
            - message: str (返回给用户的消息)
            - needs_backend: bool (是否需要转发给后台AgentActor)
            - intent: IntentType (用户意图类型)
            - draft: Optional[Dict] (草稿信息)
        """
        raise NotImplementedError

    @abstractmethod
    def parse_intent(self, user_input: str, session_id: str) -> Dict[str, Any]:
        """
        解析用户意图，生成TaskSpec

        Args:
            user_input: 用户输入文本
            session_id: 会话ID

        Returns:
            Dict containing:
            - task_spec: TaskSpec 对象
            - clarification_needed: bool
            - clarification_request: Optional[ClarificationRequest]
        """
        raise NotImplementedError

    @abstractmethod
    def create_draft(self, task_spec: TaskSpec, session_id: str, user_id: str = "default_user") -> Draft:
        """
        创建新的草稿

        Args:
            task_spec: 任务描述
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            创建的 Draft 对象
        """
        raise NotImplementedError

    @abstractmethod
    def update_draft(self, draft_id: str, updates: Dict[str, Any], user_id: str = "default_user") -> Draft:
        """
        更新草稿

        Args:
            draft_id: 草稿ID
            updates: 更新内容
            user_id: 用户ID

        Returns:
            更新后的 Draft 对象
        """
        raise NotImplementedError

    @abstractmethod
    def get_draft(self, draft_id: str, user_id: str = "default_user") -> Optional[Draft]:
        """
        获取指定草稿

        Args:
            draft_id: 草稿ID
            user_id: 用户ID

        Returns:
            Draft 对象，不存在则返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def get_drafts_by_session(self, session_id: str, user_id: str = "default_user") -> List[Draft]:
        """
        获取会话关联的所有草稿

        Args:
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            Draft 对象列表
        """
        raise NotImplementedError

    @abstractmethod
    def delete_draft(self, draft_id: str, user_id: str = "default_user") -> bool:
        """
        删除草稿

        Args:
            draft_id: 草稿ID
            user_id: 用户ID

        Returns:
            删除成功返回 True，否则返回 False
        """
        raise NotImplementedError

    @abstractmethod
    def submit_draft(self, draft_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        提交草稿，创建任务

        Args:
            draft_id: 草稿ID
            user_id: 用户ID

        Returns:
            Dict containing:
            - task_id: str
            - status: str
        """
        raise NotImplementedError

    @abstractmethod
    def generate_clarification(self, task_id: str, missing_field: str, context: Dict[str, Any]) -> ClarificationRequest:
        """
        生成澄清请求

        Args:
            task_id: 任务ID
            missing_field: 缺失的字段
            context: 上下文信息

        Returns:
            ClarificationRequest 对象
        """
        raise NotImplementedError

    @abstractmethod
    def process_clarification_response(self, task_id: str, response: Dict[str, Any], session_id: str) -> Dict[str, Any]:
        """
        处理用户对澄清请求的响应

        Args:
            task_id: 任务ID
            response: 用户响应
            session_id: 会话ID

        Returns:
            Dict containing:
            - task_id: str
            - status: str
            - requires_more_input: bool
        """
        raise NotImplementedError

    @abstractmethod
    def is_parameter_completion(self, user_input: str, session_id: str) -> bool:
        """判断用户输入是否是参数补充"""
        raise NotImplementedError

    @abstractmethod
    def identify_target_task(self, user_input: str, session_id: str) -> Optional[str]:
        """识别用户正在补充哪个任务的参数，返回task_id"""
        raise NotImplementedError

    @abstractmethod
    def pause_task_for_parameters(self, task_id: str, missing_params: List[str],
                                  task_context: Dict[str, Any], session_id: str) -> str:
        """
        后台调用：暂停任务链，等待用户补充参数

        Args:
            task_id: 任务ID
            missing_params: 缺失的参数列表
            task_context: 任务上下文（包含已有信息）
            session_id: 会话ID

        Returns:
            向用户询问参数的问题
        """
        raise NotImplementedError

    @abstractmethod
    def get_pending_tasks(self, session_id: str, user_id: str = "default_user") -> List[TaskDraft]:
        """获取用户所有等待参数补充的任务"""
        raise NotImplementedError

    @abstractmethod
    def complete_task_parameters(self, task_id: str, user_input: str, session_id: str,
                                 user_id: str = "default_user") -> Tuple[bool, Dict[str, Any]]:
        """
        补充任务参数

        Args:
            task_id: 任务ID
            user_input: 用户输入
            session_id: 会话ID
            user_id: 用户ID

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
    def restore_latest_draft(self, session_id: str, user_id: str = "default_user") -> bool:
        """Restore latest draft"""
        raise NotImplementedError

    @abstractmethod
    def save_draft(self, draft: TaskDraft, session_id: str, user_id: str = "default_user"):
        """Save current draft"""
        raise NotImplementedError

    @abstractmethod
    def clear_draft(self, session_id: str):
        """Clear current draft"""
        raise NotImplementedError
