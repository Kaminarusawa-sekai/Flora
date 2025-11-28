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


class TaskSpec:
    """
    任务规范
    定义任务的类型和参数
    """
    
    def __init__(self, task_id: str, type: str, parameters: Optional[Dict[str, Any]] = None, repeat_count: int = 1, aggregation_strategy: str = "list", **kwargs):
        """
        初始化任务规范
        
        Args:
            task_id: 任务ID
            type: 任务类型
            parameters: 任务参数
            repeat_count: 任务重复执行次数
            aggregation_strategy: 结果聚合策略
            **kwargs: 兼容旧版本的参数（content, task_metadata等）
        """
        self.task_id = task_id
        self.type = type
        
        # 处理新版本参数
        if parameters is not None:
            self.parameters = parameters
        else:
            # 处理旧版本参数（content, task_metadata等）
            self.parameters = kwargs.get("parameters", {})
            # 兼容旧版本的content字段
            if "content" in kwargs:
                self.parameters["content"] = kwargs["content"]
            # 兼容旧版本的task_metadata字段
            if "task_metadata" in kwargs:
                self.parameters["task_metadata"] = kwargs["task_metadata"]
        
        self.repeat_count = repeat_count
        self.aggregation_strategy = aggregation_strategy


class RepeatTaskRequest(BaseMessage):
    """
    重复任务请求消息
    请求重复执行一个任务并聚合结果
    """
    
    def __init__(self, source: str, destination: str, spec: TaskSpec, reply_to: str, timestamp: Optional[datetime] = None):
        """
        初始化重复任务请求消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            spec: 任务规范
            reply_to: 结果返回地址
            timestamp: 时间戳
        """
        super().__init__('repeat_task_request', source, destination, timestamp)
        self.spec = spec
        self.reply_to = reply_to
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({"spec": self.spec.__dict__, "reply_to": self.reply_to})
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RepeatTaskRequest':
        """
        从字典创建重复任务请求消息
        """
        message = super().from_dict(data)
        message.spec = TaskSpec(**data.get('spec', {}))
        message.reply_to = data.get('reply_to', '')
        return message

class UserRequestMessage(BaseMessage):
    """
    用户请求消息
    用户 -> Router -> Agent
    """
    
    def __init__(self, source: str, destination: str, user_id: str, content: str, timestamp: Optional[datetime] = None):
        """
        初始化用户请求消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            user_id: 用户ID
            content: 请求内容
            timestamp: 时间戳
        """
        super().__init__('user_request', source, destination, timestamp)
        self.user_id = user_id
        self.content = content
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "user_id": self.user_id,
            "content": self.content
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserRequestMessage':
        """
        从字典创建用户请求消息
        """
        message = super().from_dict(data)
        message.user_id = data.get('user_id', '')
        message.content = data.get('content', '')
        return message


class TaskGroupRequest(BaseMessage):
    """
    任务组请求消息
    Agent -> TaskGroupAggregator (包含一组子任务)
    """
    
    def __init__(self, source: str, destination: str, parent_task_id: str, subtasks: List[TaskSpec], strategy: str = "standard", original_sender: str = None, context: Dict[str, Any] = None, timestamp: Optional[datetime] = None):
        """
        初始化任务组请求消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            parent_task_id: 父任务ID
            subtasks: 子任务列表
            strategy: 执行策略 (e.g., "optuna", "standard")
            original_sender: 原始发送者地址
            context: 上下文参数
            timestamp: 时间戳
        """
        super().__init__('task_group_request', source, destination, timestamp)
        self.parent_task_id = parent_task_id
        self.subtasks = subtasks
        self.strategy = strategy
        self.original_sender = original_sender
        self.context = context or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "parent_task_id": self.parent_task_id,
            "subtasks": [task.__dict__ for task in self.subtasks],  # 转换为字典列表
            "strategy": self.strategy,
            "original_sender": self.original_sender,
            "context": self.context
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskGroupRequest':
        """
        从字典创建任务组请求消息
        """
        message = super().from_dict(data)
        message.parent_task_id = data.get('parent_task_id', '')
        # 从字典恢复TaskSpec对象
        subtasks = [TaskSpec(**task_dict) for task_dict in data.get('subtasks', [])]
        message.subtasks = subtasks
        message.strategy = data.get('strategy', 'standard')
        message.original_sender = data.get('original_sender')
        message.context = data.get('context', {})
        return message


class AgentTaskMessage(BaseMessage):
    """
    智能体任务消息
    Aggregator -> ExecutionActor (单任务指令)
    """
    
    def __init__(self, source: str, destination: str, task_id: str, task_type: str, content: str, context: Dict[str, Any] = None, execution_mode: str = "standard", sender_addr: str = None, timestamp: Optional[datetime] = None):
        """
        初始化智能体任务消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            task_type: 任务类型 (e.g., "LEAF", "COMPLEX")
            content: 任务内容
            context: 上下文参数
            execution_mode: 执行模式 (e.g., "standard", "connector")
            sender_addr: 发送者地址
            timestamp: 时间戳
        """
        super().__init__('agent_task', source, destination, timestamp)
        self.task_id = task_id
        self.task_type = task_type
        self.content = content
        self.context = context or {}
        self.execution_mode = execution_mode
        self.sender_addr = sender_addr
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "task_type": self.task_type,
            "content": self.content,
            "context": self.context,
            "execution_mode": self.execution_mode,
            "sender_addr": self.sender_addr
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentTaskMessage':
        """
        从字典创建智能体任务消息
        """
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.task_type = data.get('task_type', 'LEAF')
        message.content = data.get('content', '')
        message.context = data.get('context', {})
        message.execution_mode = data.get('execution_mode', 'standard')
        message.sender_addr = data.get('sender_addr')
        return message


class TaskExecutionResult(BaseMessage):
    """
    任务执行结果消息
    ExecutionActor -> Aggregator -> Agent (结果)
    """
    
    def __init__(self, source: str, destination: str, task_id: str, status: str, result_data: Any = None, error_msg: str = None, timestamp: Optional[datetime] = None):
        """
        初始化任务执行结果消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            task_id: 任务ID
            status: 执行状态 (e.g., "SUCCESS", "FAILED")
            result_data: 执行结果数据
            error_msg: 错误信息
            timestamp: 时间戳
        """
        super().__init__('task_execution_result', source, destination, timestamp)
        self.task_id = task_id
        self.status = status
        self.result_data = result_data
        self.error_msg = error_msg
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "status": self.status,
            "result_data": self.result_data,
            "error_msg": self.error_msg
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskExecutionResult':
        """
        从字典创建任务执行结果消息
        """
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.status = data.get('status', 'FAILED')
        message.result_data = data.get('result_data')
        message.error_msg = data.get('error_msg')
        return message


class ExecuteTaskMessage(BaseMessage):
    """
    执行任务消息
    用于向执行器发送任务执行请求
    """
    
    def __init__(self, source: str, destination: str, spec: TaskSpec, reply_to: str, timestamp: Optional[datetime] = None):
        """
        初始化执行任务消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            spec: 任务规范
            reply_to: 结果返回地址
            timestamp: 时间戳
        """
        super().__init__('execute_task', source, destination, timestamp)
        self.spec = spec
        self.reply_to = reply_to
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "spec": self.spec.__dict__,  # 转换为字典
            "reply_to": self.reply_to
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecuteTaskMessage':
        """
        从字典创建执行任务消息
        """
        message = super().from_dict(data)
        message.spec = TaskSpec(**data.get('spec', {}))
        message.reply_to = data.get('reply_to', '')
        return message


class TaskCompleted(TaskMessage):
    """
    任务完成消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, result: Any, timestamp: Optional[datetime] = None):
        super().__init__('task_completed', source, destination, task_id, timestamp)
        self.result = result
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({'result': self.result})
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskCompleted':
        message = super().from_dict(data)
        message.result = data.get('result')
        return message


class TaskFailed(TaskMessage):
    """
    任务失败消息
    """
    
    def __init__(self, source: str, destination: str, task_id: str, error: str, details: Optional[Dict[str, Any]] = None, original_spec: Optional[TaskSpec] = None, timestamp: Optional[datetime] = None):
        super().__init__('task_failed', source, destination, task_id, timestamp)
        self.error = error
        self.details = details or {}
        self.original_spec = original_spec
    
    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            'error': self.error,
            'details': self.details,
            'original_spec': self.original_spec.__dict__ if self.original_spec else None
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskFailed':
        message = super().from_dict(data)
        message.error = data.get('error', '')
        message.details = data.get('details', {})
        original_spec = data.get('original_spec')
        message.original_spec = TaskSpec(**original_spec) if original_spec else None
        return message


class TaskGroupResult(BaseMessage):
    """
    任务组结果消息
    包含所有任务的结果和失败信息
    """
    
    def __init__(self, source: str, destination: str, group_id: str, results: Dict[str, Any], failures: Dict[str, str], timestamp: Optional[datetime] = None):
        """
        初始化任务组结果消息
        
        Args:
            source: 消息源
            destination: 消息目的地
            group_id: 任务组ID
            results: 成功任务的结果
            failures: 失败任务的错误信息
            timestamp: 时间戳
        """
        super().__init__('task_group_result', source, destination, timestamp)
        self.group_id = group_id
        self.results = results
        self.failures = failures
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典
        """
        base_dict = super().to_dict()
        base_dict.update({
            "group_id": self.group_id,
            "results": self.results,
            "failures": self.failures
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskGroupResult':
        """
        从字典创建任务组结果消息
        """
        message = super().from_dict(data)
        message.group_id = data.get('group_id', '')
        message.results = data.get('results', {})
        message.failures = data.get('failures', {})
        return message
