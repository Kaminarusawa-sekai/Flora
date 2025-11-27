"""Agent消息模块"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from .base_message import BaseMessage


class InitMessage(BaseMessage):
    """初始化消息"""
    def __init__(self, agent_id: str, capabilities: list, memory_key: str, registry, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('init', source, destination, timestamp)
        self.agent_id = agent_id
        self.capabilities = capabilities
        self.memory_key = memory_key
        self.registry = registry
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"init_msg_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "memory_key": self.memory_key,
            "registry": str(self.registry)  # registry可能不是可序列化对象，需要转换为字符串
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InitMessage':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.agent_id = data.get('agent_id', '')
        message.capabilities = data.get('capabilities', [])
        message.memory_key = data.get('memory_key', '')
        message.registry = data.get('registry', '')
        return message


class AgentTaskMessage(BaseMessage):
    """Agent任务消息"""
    def __init__(self, task_id: str, context: dict, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('agent_task', source, destination, timestamp)
        self.task_id = task_id
        self.context = context
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"agent_task_msg_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "context": self.context
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentTaskMessage':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.context = data.get('context', {})
        return message


class SubtaskResultMessage(BaseMessage):
    """子任务结果消息"""
    def __init__(self, task_id: str, result: Any, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('subtask_result', source, destination, timestamp)
        self.task_id = task_id
        self.result = result
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"subtask_result_msg_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "result": self.result
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubtaskResultMessage':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.result = data.get('result')
        return message


class SubtaskErrorMessage(BaseMessage):
    """子任务错误消息"""
    def __init__(self, task_id: str, error: str, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('subtask_error', source, destination, timestamp)
        self.task_id = task_id
        self.error = error
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"subtask_error_msg_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "error": self.error
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubtaskErrorMessage':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.error = data.get('error', '')
        return message


class MemoryResponseMessage(BaseMessage):
    """内存响应消息"""
    def __init__(self, key: str, value: Any, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('memory_response', source, destination, timestamp)
        self.key = key
        self.value = value
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"memory_response_msg_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "key": self.key,
            "value": self.value
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryResponseMessage':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.key = data.get('key', '')
        message.value = data.get('value')
        return message


class DifySchemaRequest(BaseMessage):
    """Dify Schema请求消息"""
    def __init__(self, task_id: str, echo_payload: dict, api_key: str, base_url: str, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('dify_schema_request', source, destination, timestamp)
        self.task_id = task_id
        self.echo_payload = echo_payload
        self.api_key = api_key
        self.base_url = base_url
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"dify_schema_request_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "echo_payload": self.echo_payload,
            "api_key": self.api_key,
            "base_url": self.base_url
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DifySchemaRequest':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.echo_payload = data.get('echo_payload', {})
        message.api_key = data.get('api_key', '')
        message.base_url = data.get('base_url', '')
        return message


class DifySchemaResponse(BaseMessage):
    """Dify Schema响应消息"""
    def __init__(self, task_id: str, echo_payload: dict, input_schema: list = None, error: str = None, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('dify_schema_response', source, destination, timestamp)
        self.task_id = task_id
        self.echo_payload = echo_payload
        self.input_schema = input_schema or []
        self.error = error
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"dify_schema_response_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "echo_payload": self.echo_payload,
            "input_schema": self.input_schema,
            "error": self.error
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DifySchemaResponse':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.echo_payload = data.get('echo_payload', {})
        message.input_schema = data.get('input_schema', [])
        message.error = data.get('error')
        return message


class DifyExecuteRequest(BaseMessage):
    """Dify执行请求消息"""
    def __init__(self, task_id: str, inputs: dict, user: str, original_sender: str, api_key: str, base_url: str, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('dify_execute_request', source, destination, timestamp)
        self.task_id = task_id
        self.inputs = inputs
        self.user = user
        self.original_sender = original_sender
        self.api_key = api_key
        self.base_url = base_url
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"dify_execute_request_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "inputs": self.inputs,
            "user": self.user,
            "original_sender": self.original_sender,
            "api_key": self.api_key,
            "base_url": self.base_url
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DifyExecuteRequest':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.inputs = data.get('inputs', {})
        message.user = data.get('user', '')
        message.original_sender = data.get('original_sender', '')
        message.api_key = data.get('api_key', '')
        message.base_url = data.get('base_url', '')
        return message


class DifyExecuteResponse(BaseMessage):
    """Dify执行响应消息"""
    def __init__(self, task_id: str, outputs: dict, workflow_run_id: str, status: str, error: str = None, original_sender: str = None, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('dify_execute_response', source, destination, timestamp)
        self.task_id = task_id
        self.outputs = outputs
        self.workflow_run_id = workflow_run_id
        self.status = status
        self.error = error
        self.original_sender = original_sender
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"dify_execute_response_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "outputs": self.outputs,
            "workflow_run_id": self.workflow_run_id,
            "status": self.status,
            "error": self.error,
            "original_sender": self.original_sender
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DifyExecuteResponse':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.outputs = data.get('outputs', {})
        message.workflow_run_id = data.get('workflow_run_id', '')
        message.status = data.get('status', '')
        message.error = data.get('error')
        message.original_sender = data.get('original_sender')
        return message


class DataQueryRequest(BaseMessage):
    """数据查询请求消息"""
    def __init__(self, request_id: str, query: str, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('data_query_request', source, destination, timestamp)
        self.request_id = request_id
        self.query = query
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"data_query_request_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "request_id": self.request_id,
            "query": self.query
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataQueryRequest':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.request_id = data.get('request_id', '')
        message.query = data.get('query', '')
        return message


class DataQueryResponse(BaseMessage):
    """数据查询响应消息"""
    def __init__(self, request_id: str, result: Any = None, error: str = None, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('data_query_response', source, destination, timestamp)
        self.request_id = request_id
        self.result = result
        self.error = error
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"data_query_response_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "request_id": self.request_id,
            "result": self.result,
            "error": self.error
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DataQueryResponse':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.request_id = data.get('request_id', '')
        message.result = data.get('result')
        message.error = data.get('error')
        return message


class McpFallbackRequest(BaseMessage):
    """MCP回退请求消息"""
    def __init__(self, task_id: str, context: dict, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('mcp_fallback_request', source, destination, timestamp)
        self.task_id = task_id
        self.context = context
    
    def _generate_id(self) -> str:
        """生成消息ID"""
        import uuid
        return f"mcp_fallback_request_{uuid.uuid4()}"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "context": self.context
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'McpFallbackRequest':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.context = data.get('context', {})
        return message
