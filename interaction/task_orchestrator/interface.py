"""任务协调器接口定义"""
from typing import Dict, Optional, Any, List
from abc import ABC, abstractmethod
from capabilities.capability_base import CapabilityBase
from interaction.common.models import Task, TaskSpec, ClarificationRequest


class ITaskOrchestratorCapability(CapabilityBase):
    """任务协调器能力接口"""

    @abstractmethod
    def execute_task(self, task_spec: TaskSpec, session_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        执行任务

        Args:
            task_spec: 任务描述
            session_id: 会话ID
            user_id: 用户ID

        Returns:
            Dict containing:
            - task_id: str
            - status: str (running, paused, completed, failed, awaiting_input)
        """
        raise NotImplementedError

    @abstractmethod
    def parse_intent_to_task_spec(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """
        解析用户意图为TaskSpec

        Args:
            session_id: 会话ID
            user_message: 用户消息

        Returns:
            Dict containing:
            - task_spec: TaskSpec 对象
            - clarification_needed: bool
            - clarification_request: Optional[ClarificationRequest]
        """
        raise NotImplementedError

    @abstractmethod
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务信息

        Args:
            task_id: 任务ID

        Returns:
            Task 对象，不存在则返回 None
        """
        raise NotImplementedError

    @abstractmethod
    def get_tasks_by_session(self, session_id: str) -> List[Task]:
        """
        获取会话关联的所有任务

        Args:
            session_id: 会话ID

        Returns:
            Task 对象列表
        """
        raise NotImplementedError

    @abstractmethod
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务

        Args:
            task_id: 任务ID

        Returns:
            Dict containing:
            - task_id: str
            - status: str (cancelled)
        """
        raise NotImplementedError

    @abstractmethod
    def pause_task(self, task_id: str) -> Dict[str, Any]:
        """
        暂停任务

        Args:
            task_id: 任务ID

        Returns:
            Dict containing:
            - task_id: str
            - status: str (paused)
        """
        raise NotImplementedError

    @abstractmethod
    def resume_task(self, task_id: str, resume_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        恢复任务

        Args:
            task_id: 任务ID
            resume_input: 恢复任务所需的输入

        Returns:
            Dict containing:
            - task_id: str
            - status: str (running, completed, failed, awaiting_input)
        """
        raise NotImplementedError

    @abstractmethod
    def retry_task(self, task_id: str) -> Dict[str, Any]:
        """
        重试任务

        Args:
            task_id: 任务ID

        Returns:
            Dict containing:
            - task_id: str
            - status: str (running)
        """
        raise NotImplementedError

    @abstractmethod
    def request_task_input(self, task_id: str, field: str, prompt: str, input_type: str = "text", 
                          options: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        请求任务输入

        Args:
            task_id: 任务ID
            field: 需要输入的字段
            prompt: 提示信息
            input_type: 输入类型
            options: 可选选项列表

        Returns:
            Dict containing:
            - status: str
            - clarification_request: ClarificationRequest
        """
        raise NotImplementedError

    @abstractmethod
    def handle_executor_response(self, task_id: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务执行器的响应

        Args:
            task_id: 任务ID
            response: 执行器响应

        Returns:
            Dict containing:
            - task_id: str
            - status: str
            - requires_input: bool
            - clarification_request: Optional[ClarificationRequest]
        """
        raise NotImplementedError

    @abstractmethod
    def add_task_log(self, task_id: str, step: str, message: str, level: str = "info") -> None:
        """
        添加任务日志

        Args:
            task_id: 任务ID
            step: 执行步骤
            message: 日志消息
            level: 日志级别
        """
        raise NotImplementedError

    @abstractmethod
    def get_task_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        获取任务日志

        Args:
            task_id: 任务ID

        Returns:
            日志列表
        """
        raise NotImplementedError
