"""核心数据模型定义"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Optional, List, Any, Union


@dataclass
class TaskLog:
    """任务日志模型"""
    timestamp: datetime = field(default_factory=datetime.now)
    step: str
    message: str
    level: str = "info"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "step": self.step,
            "message": self.message,
            "level": self.level
        }


@dataclass
class TaskSpec:
    """
    任务描述协议
    
    Attributes:
        task_type: 任务类型（如 'send_email', 'data_export'）
        params: 结构化参数
        requires_confirmation: 是否需要用户确认
        metadata: 元数据
    """
    task_type: str
    params: Dict[str, Any]
    requires_confirmation: bool = True
    metadata: Optional[Dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_type": self.task_type,
            "params": self.params,
            "requires_confirmation": self.requires_confirmation,
            "metadata": self.metadata
        }


@dataclass
class Draft:
    """
    草稿模型
    
    Attributes:
        draft_id: 草稿ID
        session_id: 会话ID
        task_spec: 任务描述
        status: 草稿状态（editing, pending_confirmation, submitted）
        created_at: 创建时间
        updated_at: 更新时间
    """
    draft_id: str
    session_id: str
    task_spec: TaskSpec
    status: str  # editing, pending_confirmation, submitted
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draft_id": self.draft_id,
            "session_id": self.session_id,
            "task_spec": self.task_spec.to_dict(),
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class Task:
    """
    已提交任务模型
    
    Attributes:
        task_id: 任务ID
        draft_id: 关联的草稿ID
        status: 任务状态（running, paused, completed, failed, awaiting_input）
        current_step: 当前执行步骤
        result: 执行结果
        error: 错误信息
        logs: 任务日志
        created_at: 创建时间
        updated_at: 更新时间
    """
    task_id: str
    draft_id: str
    status: str  # running, paused, completed, failed, awaiting_input
    current_step: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    logs: List[TaskLog] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "draft_id": self.draft_id,
            "status": self.status,
            "current_step": self.current_step,
            "result": self.result,
            "error": self.error,
            "logs": [log.to_dict() for log in self.logs],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ConversationSession:
    """
    对话会话模型
    
    Attributes:
        session_id: 会话ID
        user_id: 用户ID
        drafts: 当前会话关联的草稿
        active_task_id: 当前激活的任务ID
        created_at: 创建时间
        updated_at: 更新时间
    """
    session_id: str
    user_id: str
    drafts: List[Draft] = field(default_factory=list)
    active_task_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "drafts": [draft.to_dict() for draft in self.drafts],
            "active_task_id": self.active_task_id,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


@dataclass
class ClarificationRequest:
    """
    澄清请求模型
    
    Attributes:
        session_id: 会话ID
        task_id: 任务ID
        field: 需要澄清的字段
        prompt: 澄清问题
        input_type: 输入类型（text, select, date等）
        options: 可选的选项列表
    """
    session_id: str
    task_id: str
    field: str
    prompt: str
    input_type: str = "text"
    options: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "task_id": self.task_id,
            "field": self.field,
            "prompt": self.prompt,
            "input_type": self.input_type,
            "options": self.options
        }
