"""Execution Actor - 具体执行处理者
负责连接外部系统和内部函数进行具体执行
⑪ 具体执行：
- 连接外部系统（HTTP、Dify等）
- 处理不同的执行步骤（Dify需要先获取参数再执行）
- 调用内部能力函数
- 返回执行结果
"""
from typing import Dict, Any, Optional, List, Union
from thespian.actors import Actor
import logging
from typing import Dict, Any, Optional, List, Union

from ..common.messages.task_messages import ExecuteTaskMessage, ExecutionResultMessage
from ..capabilities import get_capability
from ..capabilities.excution import BaseExecution
from ..events.event_bus import event_bus
from ..events.event_types import EventType

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ExecutionActor(Actor):
    """
    ⑪ 具体执行器
    负责实际调用外部系统和内部函数
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._pending_requests = {}  # task_id -> request_info
        self._excution:BaseExecution = get_capability("execution", BaseExecution)  # 添加连接器管理器实例
        self.logger.info("ExecutionActor initialized")
        self.task_id=None
        self.trace_id=None
        self.task_path=None

    def receiveMessage(self, msg: Any, sender: str) -> None:
        """
        接收消息并处理

        Args:
            msg: 消息内容
            sender: 发送者
        """
        try:
            if isinstance(msg, ExecuteTaskMessage):
                # 处理执行任务消息
                self._handle_execute_message(msg, sender)
            else:
                self.logger.warning(f"Unknown message format: {type(msg)}")
                # 如果不是预期的消息类型，不处理

        except Exception as e:
            self.logger.error(f"ExecutionActor error: {e}")
            if isinstance(msg, ExecuteTaskMessage):
                self._send_error(msg.task_id, str(e), msg.reply_to)

    def _handle_execute_message(self, msg: ExecuteTaskMessage, sender: str) -> None:
        """
        处理执行任务消息

        Args:
            msg: 执行任务消息对象
            sender: 发送者
        """
        self.task_id = msg.task_id
        self.trace_id = msg.trace_id
        self.task_path = msg.task_path
        capability = msg.capability
        parameters = msg.params
        reply_to = msg.reply_to
        
        # 复用现有执行逻辑
        self._execute(capability, self.task_id, parameters, reply_to)
    
    def _execute(self, capability: str, task_id: str, parameters: Dict[str, Any], reply_to: str) -> None:
        """
        执行任务的核心逻辑
        
        Args:
            capability: 能力名称
            task_id: 任务ID
            parameters: 参数
            reply_to: 回复地址
        """
        context = parameters.get("context", {})
        key = context.get("key", "")

        self.logger.info(f"⑪ 具体执行: task={task_id}, capability={capability}")

        # 保存请求信息
        self._pending_requests[task_id] = {
            "capability": capability,
            "parameters": parameters,
            "reply_to": reply_to
        }

        # 发布执行开始事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.CAPABILITY_EXECUTED.value,
            source="ExecutionActor",
            agent_id="system",
            data={"capability": capability, "status": "started"}
        )

        # 根据能力类型选择执行方式
        if capability == "dify" or capability == "dify_workflow":
            self._execute_dify(task_id, parameters, reply_to)
        elif capability == "http" or capability.startswith("http_"):
            self._execute_http(task_id, parameters, reply_to)
        else:
            self._send_error(task_id, f"Capability {capability} not found", reply_to)

    def _execute_dify(self, task_id: str, parameters: Dict[str, Any], reply_to: str) -> None:
        """
        执行 Dify 工作流

        Args:
            task_id: 任务ID
            parameters: 参数
            reply_to: 回复地址
        """
        self.logger.info(f"Executing Dify workflow for task {task_id}")

        try:
            # 调用connector_manager执行Dify工作流
            result = self._excution.execute(
                connector_name="dify",
                inputs=parameters.get("inputs", {}),
                params=parameters
            )
            status = result.get("status")
            # 处理执行结果
            if status == "NEED_INPUT":
                # 需要补充参数
                missing_params = result["missing"]
                missing_params_descriptions = [str({"name": k, "description": v}) for k, v in missing_params.items()]
                self._send_missing_parameters(task_id, missing_params_descriptions, parameters, reply_to)
            elif status == "SUCCESS":
                self._send_success(task_id, result["result"], reply_to)
            elif status == "FAILURE":
                # 可重试的失败
                self._send_failure(task_id, result["error"], reply_to)
            elif status == "ERROR":
                # 不可重试的错误
                self._send_error(task_id, result["error"], reply_to)
            else:
                self._send_error(task_id, f"Unknown status from connector: {status}", reply_to)

        except Exception as e:
            self.logger.exception(f"Dify execution failed: {e}")
            self._send_error(task_id, str(e), reply_to)

    def _execute_http(self, task_id: str, parameters: Dict[str, Any], reply_to: str) -> None:
        """
        执行 HTTP 请求

        Args:
            task_id: 任务ID
            parameters: 参数，包含 url, method, headers, data等
            reply_to: 回复地址
        """
        self.logger.info(f"Executing HTTP request for task {task_id}")

        try:
            # 调用connector_manager执行HTTP请求
            result = self._excution.execute(
                connector_name="http",
                operation_name="execute",
                inputs=parameters.get("data", {}),
                params=parameters
            )
            
            # 处理执行结果
            if result["result"]["status"] == "NEED_INPUT":
                # 需要补充参数
                missing_params = result["result"]["missing"]
                self._send_missing_parameters(task_id, missing_params, parameters, reply_to)
            else:
                # 执行成功
                self._send_success(task_id, result["result"], reply_to)

        except Exception as e:
            self.logger.error(f"HTTP request failed: {e}")
            self._send_error(task_id, f"HTTP request failed: {str(e)}", reply_to)
    
    
    def _send_missing_parameters(self, task_id: str, missing_params: List[str],
                                   parameters: Dict[str, Any], reply_to: str) -> None:
        """
        请求补充缺失的参数

        Args:
            task_id: 任务ID
            missing_params: 缺失参数列表
            parameters: 当前参数
            reply_to: 回复地址
        """
        self.logger.info(f"Task {task_id} missing parameters: {missing_params}")
        
        
        # 使用新的执行结果消息类型返回需要输入的状态
        response = ExecutionResultMessage(
            task_id=self.task_id,
            trace_id=self.trace_id,
            task_path=self.task_path,
            status="NEED_INPUT",
            result=None,
            error=None,
            agent_id="system",
            missing_params=missing_params
        )
        
        self.send(reply_to, response)
        
        # 发布任务暂停事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_PAUSED.value,
            source="ExecutionActor",
            agent_id="system",
            data={"missing_params": missing_params}
        )

   
  

    def _send_success(self, task_id: str, result: Any, reply_to: str) -> None:
        """发送成功结果"""
        # 使用新的执行结果消息类型
        response = ExecutionResultMessage(
            task_id=task_id,
            trace_id=self.trace_id,
            task_path=self.task_path,
            status="SUCCESS",
            result=result,
            error=None,
            agent_id="system"
        )

        self.send(reply_to, response)

        # 发布执行成功事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.CAPABILITY_EXECUTED.value,
            source="ExecutionActor",
            agent_id="system",
            data={"status": "success", "result": result}
        )

        # 清理请求信息
        if task_id in self._pending_requests:
            del self._pending_requests[task_id]

    def _send_failure(self, task_id: str, error: str, reply_to: str) -> None:
        """发送可重试的失败结果"""
        response = ExecutionResultMessage(
            task_id=task_id,
            trace_id=self.trace_id,
            task_path=self.task_path,
            status="FAILED",          # 或 "RETRYABLE_FAILURE"
            result=None,
            error=error,
            agent_id="system"
        )
        self.send(reply_to, response)
        # 发布可重试事件（调度器可监听并重试）
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.CAPABILITY_FAILED.value,
            source="ExecutionActor",
            agent_id="system",
            data={"error": error, "retryable": True}
        )
        if task_id in self._pending_requests:
            del self._pending_requests[task_id]

    def _send_error(self, task_id: str, error: str, reply_to: str) -> None:
        """发送错误响应"""
        # 使用新的执行结果消息类型
        response = ExecutionResultMessage(
            task_id=task_id,
            trace_id=self.trace_id,
            task_path=self.task_path,
            status="FAILED",
            result=None,
            error=error,
            agent_id="system"
        )

        self.send(reply_to, response)

        # 发布执行失败事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.CAPABILITY_ERROR.value,
            source="ExecutionActor",
            agent_id="system",
            data={"status": "failed", "error": error}
        )

        # 清理请求信息
        if task_id in self._pending_requests:
            del self._pending_requests[task_id]
