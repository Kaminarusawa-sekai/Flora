"""连接器能力消息模块"""
from typing import Dict, Any, Optional
from datetime import datetime
from .base_message import BaseMessage


class ExecuteConnectorRequest(BaseMessage):
    """执行连接器请求（基础能力 - 所有连接器必须响应）"""
    def __init__(self, task_id: str, params: Dict[str, Any], reply_to: str = "", source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('execute_connector_request', source, destination, timestamp)
        self.task_id = task_id
        self.params = params
        self.reply_to = reply_to

    def _generate_id(self) -> str:
        import uuid
        return f"exec_conn_req_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "params": self.params,
            "reply_to": self.reply_to
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExecuteConnectorRequest':
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.params = data.get('params', {})
        message.reply_to = data.get('reply_to', '')
        return message


class PrepareConnectorRequest(BaseMessage):
    """准备连接器请求（可选能力 - 支持准备阶段的连接器才处理）"""
    def __init__(self, task_id: str, context: Dict[str, Any], reply_to: str = "", source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('prepare_connector_request', source, destination, timestamp)
        self.task_id = task_id
        self.context = context
        self.reply_to = reply_to

    def _generate_id(self) -> str:
        import uuid
        return f"prep_conn_req_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "context": self.context,
            "reply_to": self.reply_to
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrepareConnectorRequest':
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.context = data.get('context', {})
        message.reply_to = data.get('reply_to', '')
        return message


class CancelConnectorRequest(BaseMessage):
    """取消连接器请求（可选能力 - 支持中断/取消）"""
    def __init__(self, task_id: str, reply_to: str = "", source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('cancel_connector_request', source, destination, timestamp)
        self.task_id = task_id
        self.reply_to = reply_to

    def _generate_id(self) -> str:
        import uuid
        return f"cancel_conn_req_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "reply_to": self.reply_to
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CancelConnectorRequest':
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.reply_to = data.get('reply_to', '')
        return message


class GetConnectorStatusRequest(BaseMessage):
    """获取连接器状态请求（可选能力 - 支持状态查询）"""
    def __init__(self, task_id: str, reply_to: str = "", source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('get_connector_status_request', source, destination, timestamp)
        self.task_id = task_id
        self.reply_to = reply_to

    def _generate_id(self) -> str:
        import uuid
        return f"status_conn_req_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "reply_to": self.reply_to
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GetConnectorStatusRequest':
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.reply_to = data.get('reply_to', '')
        return message


class InvokeConnectorRequest(BaseMessage):
    """调用连接器请求消息"""
    def __init__(self, connector_name: str, operation_name: str, inputs: Dict[str, Any], params: Dict[str, Any] = None, reply_to: str = "", source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('invoke_connector_request', source, destination, timestamp)
        self.connector_name = connector_name
        self.operation_name = operation_name
        self.inputs = inputs
        self.params = params or {}
        self.reply_to = reply_to

    def _generate_id(self) -> str:
        """生成请求ID"""
        import uuid
        return f"invoke_req_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        base_dict = super().to_dict()
        base_dict.update({"connector_name": self.connector_name, "operation_name": self.operation_name, "inputs": self.inputs, "params": self.params, "reply_to": self.reply_to})
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'InvokeConnectorRequest':
        """从字典创建消息"""
        message = super().from_dict(data)
        message.connector_name = data.get('connector_name', '')
        message.operation_name = data.get('operation_name', '')
        message.inputs = data.get('inputs', {})
        message.params = data.get('params', {})
        message.reply_to = data.get('reply_to', '')
        return message


class ConnectorResult(BaseMessage):
    """连接器执行结果（统一结果格式）"""
    def __init__(self, task_id: str, result: Any, status: str = "success", workflow_run_id: Optional[str] = None, original_sender: Optional[str] = None, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('connector_result', source, destination, timestamp)
        self.task_id = task_id
        self.result = result
        self.status = status
        self.workflow_run_id = workflow_run_id
        self.original_sender = original_sender

    def _generate_id(self) -> str:
        import uuid
        return f"conn_result_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "result": self.result,
            "status": self.status,
            "workflow_run_id": self.workflow_run_id,
            "original_sender": self.original_sender
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectorResult':
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.result = data.get('result')
        message.status = data.get('status', 'success')
        message.workflow_run_id = data.get('workflow_run_id')
        message.original_sender = data.get('original_sender')
        return message


class ConnectorError(BaseMessage):
    """连接器执行错误（统一错误格式）"""
    def __init__(self, task_id: str, error: str, details: Optional[str] = None, original_sender: Optional[str] = None, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('connector_error', source, destination, timestamp)
        self.task_id = task_id
        self.error = error
        self.details = details
        self.original_sender = original_sender

    def _generate_id(self) -> str:
        import uuid
        return f"conn_error_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "error": self.error,
            "details": self.details,
            "original_sender": self.original_sender
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectorError':
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.error = data.get('error', '')
        message.details = data.get('details')
        message.original_sender = data.get('original_sender')
        return message


class PrepareConnectorResponse(BaseMessage):
    """准备连接器响应"""
    def __init__(self, task_id: str, result: Dict[str, Any], status: str = "success", error: Optional[str] = None, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('prepare_connector_response', source, destination, timestamp)
        self.task_id = task_id
        self.result = result
        self.status = status
        self.error = error

    def _generate_id(self) -> str:
        import uuid
        return f"prep_conn_res_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "result": self.result,
            "status": self.status,
            "error": self.error
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PrepareConnectorResponse':
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.result = data.get('result', {})
        message.status = data.get('status', 'success')
        message.error = data.get('error')
        return message


class ConnectorStatusResponse(BaseMessage):
    """连接器状态响应"""
    def __init__(self, task_id: str, status: str, details: Optional[Dict[str, Any]] = None, source: str = "", destination: str = "", timestamp: Optional[datetime] = None):
        super().__init__('connector_status_response', source, destination, timestamp)
        self.task_id = task_id
        self.status = status
        self.details = details

    def _generate_id(self) -> str:
        import uuid
        return f"conn_status_res_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "task_id": self.task_id,
            "status": self.status,
            "details": self.details
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectorStatusResponse':
        message = super().from_dict(data)
        message.task_id = data.get('task_id', '')
        message.status = data.get('status', '')
        message.details = data.get('details')
        return message


class ConnectorExecutionSuccess(BaseMessage):
    """
    所有连接器执行成功时返回此消息
    """
    def __init__(self, 
                 connector_name: str,     # 如 "dify_sales"
                 result: Any,             # 原始结果（dict/list/str 等）
                 metadata: Optional[dict] = None,  # 可选：耗时、token用量等
                 source: str = "", 
                 destination: str = "", 
                 timestamp: Optional[datetime] = None):
        super().__init__('connector_execution_success', source, destination, timestamp)
        self.connector_name = connector_name
        self.result = result
        self.metadata = metadata or {}

    def _generate_id(self) -> str:
        import uuid
        return f"conn_exec_success_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "connector_name": self.connector_name,
            "result": self.result,
            "metadata": self.metadata
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectorExecutionSuccess':
        message = super().from_dict(data)
        message.connector_name = data.get('connector_name', '')
        message.result = data.get('result')
        message.metadata = data.get('metadata', {})
        return message


class ConnectorExecutionFailure(BaseMessage):
    """
    所有连接器执行失败时返回此消息
    """
    def __init__(self, 
                 connector_name: str, 
                 error: str, 
                 error_code: Optional[str] = None, 
                 original_request: Any = None,  # 用于重试
                 source: str = "", 
                 destination: str = "", 
                 timestamp: Optional[datetime] = None):
        super().__init__('connector_execution_failure', source, destination, timestamp)
        self.connector_name = connector_name
        self.error = error
        self.error_code = error_code
        self.original_request = original_request

    def _generate_id(self) -> str:
        import uuid
        return f"conn_exec_failure_{uuid.uuid4()}"

    def to_dict(self) -> Dict[str, Any]:
        base_dict = super().to_dict()
        base_dict.update({
            "connector_name": self.connector_name,
            "error": self.error,
            "error_code": self.error_code,
            "original_request": self.original_request
        })
        return base_dict

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConnectorExecutionFailure':
        message = super().from_dict(data)
        message.connector_name = data.get('connector_name', '')
        message.error = data.get('error', '')
        message.error_code = data.get('error_code')
        message.original_request = data.get('original_request')
        return message
