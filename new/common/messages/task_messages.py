"""任务消息模块"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_message import BaseMessage


class TaskMessage(BaseMessage):
    """
    任务相关消息的基类
    """
    
    def __init__(self, message_type: str, source: str, destination: str, task_id: str, timestamp: Optional[datetime] = None):
        """
        初始化任务消息
        
        Args:
            message_type: 消息类型
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            timestamp: 时间戳
        """
        super().__init__(message_type, source, destination, timestamp)
        self.task_id = task_id
    
    def _generate_id(self) -> str:
        """
        生成消息ID
        """
        import uuid
        return f"task_msg_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskMessage':
        """
        从字典创建任务消息
        """
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        return message


class TaskCreatedMessage(TaskMessage):
    """
    任务创建消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, task_type: str, parameters: Dict[str, Any], priority: int = 0, timestamp: Optional[datetime] = None):
        """
        初始化任务创建消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            task_type: 任务类型
            parameters: 任务参数
            priority: 任务优先级
            timestamp: 时间戳
        """
        super().__init__('task_created', source, destination, task_id, timestamp)
        self.task_type = task_type
        self.parameters = parameters
        self.priority = priority
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "task_type": self.task_type,
            "parameters": self.parameters,
            "priority": self.priority
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskCreatedMessage':
        """
        从字典创建任务创建消息
        """
        message = super().from_dict(data)
        message.task_type = data.get('task_type', '')
        message.parameters = data.get('parameters', {})
        message.priority = data.get('priority', 0)
        return message


class TaskStartedMessage(TaskMessage):
    """
    任务开始消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, agent_id: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        初始化任务开始消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            agent_id: 执行任务的智能体ID
            timestamp: 时间戳
        """
        super().__init__('task_started', source, destination, task_id, timestamp)
        self.agent_id = agent_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "agent_id": self.agent_id
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskStartedMessage':
        """
        从字典创建任务开始消息
        """
        message = super().from_dict(data)
        message.agent_id = data.get('agent_id')
        return message


class TaskCompletedMessage(TaskMessage):
    """
    任务完成消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, result: Any, agent_id: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        初始化任务完成消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            result: 任务结果
            agent_id: 执行任务的智能体ID
            timestamp: 时间戳
        """
        super().__init__('task_completed', source, destination, task_id, timestamp)
        self.result = result
        self.agent_id = agent_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "result": self.result,
            "agent_id": self.agent_id
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskCompletedMessage':
        """
        从字典创建任务完成消息
        """
        message = super().from_dict(data)
        message.result = data.get('result')
        message.agent_id = data.get('agent_id')
        return message


class TaskFailedMessage(TaskMessage):
    """
    任务失败消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, error: str, details: Optional[Dict[str, Any]] = None, agent_id: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        初始化任务失败消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            error: 错误信息
            details: 错误详情
            agent_id: 执行任务的智能体ID
            timestamp: 时间戳
        """
        super().__init__('task_failed', source, destination, task_id, timestamp)
        self.error = error
        self.details = details or {}
        self.agent_id = agent_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "error": self.error,
            "details": self.details,
            "agent_id": self.agent_id
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskFailedMessage':
        """
        从字典创建任务失败消息
        """
        message = super().from_dict(data)
        message.error = data.get('error', '')
        message.details = data.get('details', {})
        message.agent_id = data.get('agent_id')
        return message


class TaskProgressMessage(TaskMessage):
    """
    任务进度消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, progress: float, status: Optional[str] = None, agent_id: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        初始化任务进度消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            progress: 任务进度（0-1）
            status: 状态描述
            agent_id: 执行任务的智能体ID
            timestamp: 时间戳
        """
        super().__init__('task_progress', source, destination, task_id, timestamp)
        self.progress = min(max(0.0, progress), 1.0)  # 确保进度在0-1范围内
        self.status = status
        self.agent_id = agent_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "progress": self.progress,
            "status": self.status,
            "agent_id": self.agent_id
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskProgressMessage':
        """
        从字典创建任务进度消息
        """
        message = super().from_dict(data)
        message.progress = data.get('progress', 0.0)
        message.status = data.get('status')
        message.agent_id = data.get('agent_id')
        return message


class TaskCancelledMessage(TaskMessage):
    """
    任务取消消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, reason: Optional[str] = None, agent_id: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        初始化任务取消消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            reason: 取消原因
            agent_id: 执行任务的智能体ID
            timestamp: 时间戳
        """
        super().__init__('task_cancelled', source, destination, task_id, timestamp)
        self.reason = reason
        self.agent_id = agent_id
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "reason": self.reason,
            "agent_id": self.agent_id
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskCancelledMessage':
        """
        从字典创建任务取消消息
        """
        message = super().from_dict(data)
        message.reason = data.get('reason')
        message.agent_id = data.get('agent_id')
        return message


class SubtaskSpawnedMessage(TaskMessage):
    """
    子任务生成消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, subtask_id: str, subtask_type: str, parameters: Dict[str, Any], priority: int = 0, timestamp: Optional[datetime] = None):
        """
        初始化子任务生成消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 父任务ID
            subtask_id: 子任务ID
            subtask_type: 子任务类型
            parameters: 子任务参数
            priority: 子任务优先级
            timestamp: 时间戳
        """
        super().__init__('subtask_spawned', source, destination, task_id, timestamp)
        self.subtask_id = subtask_id
        self.subtask_type = subtask_type
        self.parameters = parameters
        self.priority = priority
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "subtask_id": self.subtask_id,
            "subtask_type": self.subtask_type,
            "parameters": self.parameters,
            "priority": self.priority
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubtaskSpawnedMessage':
        """
        从字典创建子任务生成消息
        """
        message = super().from_dict(data)
        message.subtask_id = data.get('subtask_id', '')
        message.subtask_type = data.get('subtask_type', '')
        message.parameters = data.get('parameters', {})
        message.priority = data.get('priority', 0)
        return message
