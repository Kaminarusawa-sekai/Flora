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

from capabilities import get_capability
from capabilities.excution import BaseExecution
from events.event_bus import event_bus
from events.event_types import EventType

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

    def receiveMessage(self, msg: Any, sender: str) -> None:
        """
        接收消息并处理

        Args:
            msg: 消息内容
            sender: 发送者
        """
        try:
            if isinstance(msg, dict):
                msg_type = msg.get("type")

                if msg_type == "execute":
                    # ⑪ 具体执行请求
                    self._handle_execute(msg, sender)
                elif msg_type == "resume_execution":
                    # 恢复暂停的任务执行
                    self._handle_resume_execution(msg, sender)
                else:
                    self.logger.warning(f"Unknown message type: {msg_type}")
                    self._send_error(msg.get("task_id", "unknown"),
                                   f"Unknown message type: {msg_type}",
                                   msg.get("reply_to", sender))
            else:
                self.logger.warning(f"Unknown message format: {type(msg)}")

        except Exception as e:
            self.logger.error(f"ExecutionActor error: {e}")
            task_id = msg.get("task_id", "unknown") if isinstance(msg, dict) else "unknown"
            reply_to = msg.get("reply_to", sender) if isinstance(msg, dict) else sender
            self._send_error(task_id, str(e), reply_to)

    def _handle_execute(self, msg: Dict[str, Any], sender: str) -> None:
        """
        ⑪ 具体执行 - 根据能力类型选择执行方式

        Args:
            msg: 执行消息，包含 task_id, capability, parameters, reply_to
            sender: 发送者
        """
        task_id = msg.get("task_id")
        capability = msg.get("capability")
        context = msg.get("context", {})
        key = context.get("key", "")
        parameters = msg.get("params", {})
        reply_to = msg.get("sender", sender)

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
        elif capability == "data" or capability == "data_query":
            self._execute_data_query(task_id, parameters, reply_to)
        else:
            # 尝试从能力注册表获取并执行
            self._execute_capability(task_id, capability, parameters, reply_to)

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
            
            # 处理执行结果
            if result["status"] == "NEED_INPUT":
                # 需要补充参数
                missing_params = result["missing"]
                self._request_missing_parameters(task_id, missing_params, parameters, reply_to)
            else:
                # 执行成功
                self._send_success(task_id, result["result"], reply_to)

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
                self._request_missing_parameters(task_id, missing_params, parameters, reply_to)
            else:
                # 执行成功
                self._send_success(task_id, result["result"], reply_to)

        except Exception as e:
            self.logger.error(f"HTTP request failed: {e}")
            self._send_error(task_id, f"HTTP request failed: {str(e)}", reply_to)

    def _execute_data_query(self, task_id: str, parameters: Dict[str, Any], reply_to: str) -> None:
        """
        执行数据查询

        Args:
            task_id: 任务ID
            parameters: 参数
            reply_to: 回复地址
        """
        self.logger.info(f"Executing data query for task {task_id}")

        try:
            # 调用connector_manager执行数据查询
            result = self._excution.execute(
                connector_name="data_query",
                operation_name="execute",
                inputs={},
                params=parameters
            )
            
            # 处理执行结果
            if result["result"]["status"] == "NEED_INPUT":
                # 需要补充参数
                missing_params = result["result"]["missing"]
                self._request_missing_parameters(task_id, missing_params, parameters, reply_to)
            else:
                # 执行成功
                self._send_success(task_id, result["result"], reply_to)

        except Exception as e:
            self.logger.error(f"Data query failed: {e}")
            self._send_error(task_id, f"Data query failed: {str(e)}", reply_to)

    def _execute_capability(self, task_id: str, capability: str,
                          parameters: Dict[str, Any], reply_to: str) -> None:
        """
        执行通用能力函数

        Args:
            task_id: 任务ID
            capability: 能力名称
            parameters: 参数
            reply_to: 回复地址
        """
        self.logger.info(f"Executing capability {capability} for task {task_id}")

        try:
            # 从能力注册表获取能力
            capability_instance = get_capability(capability, expected_type=Any)

            if capability_instance and hasattr(capability_instance, 'execute'):
                # 调用能力的execute方法
                result = capability_instance.execute(
                    context=parameters.get("context", {}),
                    memory=parameters.get("memory_context", {})
                )
                self._send_success(task_id, result, reply_to)
            else:
                self._send_error(task_id, f"Capability {capability} not found or not executable", reply_to)

        except Exception as e:
            self.logger.error(f"Capability execution failed: {e}")
            self._send_error(task_id, f"Capability execution failed: {str(e)}", reply_to)

    def _handle_resume_execution(self, msg: Dict[str, Any], sender: str) -> None:
        """
        处理恢复执行请求

        Args:
            msg: 包含 task_id, parameters, reply_to
            sender: 发送者
        """
        task_id = msg.get("task_id")
        parameters = msg.get("parameters", {})
        reply_to = msg.get("reply_to", sender)

        self.logger.info(f"Resuming execution for task {task_id}")

        # 从pending_requests中获取原始请求信息
        if task_id not in self._pending_requests:
            self.logger.warning(f"Task {task_id} not found in pending requests")
            self._send_error(task_id, "Task not found in pending requests", reply_to)
            return

        req_info = self._pending_requests[task_id]
        capability = req_info["capability"]

        # 合并补充的参数
        original_params = req_info["parameters"]
        original_params.update(parameters)

        self.logger.info(f"Resuming {capability} execution with updated parameters")

        # 根据能力类型继续执行
        if capability == "dify" or capability == "dify_workflow":
            self._execute_dify(task_id, original_params, reply_to)
        elif capability == "http" or capability.startswith("http_"):
            self._execute_http(task_id, original_params, reply_to)
        elif capability == "data" or capability == "data_query":
            self._execute_data_query(task_id, original_params, reply_to)
        else:
            self._execute_capability(task_id, capability, original_params, reply_to)


    def _request_missing_parameters(self, task_id: str, missing_params: List[str],
                                   parameters: Dict[str, Any], reply_to: str) -> None:
        """
        请求补充缺失的参数（通过ConversationManager）

        Args:
            task_id: 任务ID
            missing_params: 缺失参数列表
            parameters: 当前参数
            reply_to: 回复地址（AgentActor的地址）
        """
        self.logger.info(f"Task {task_id} missing parameters: {missing_params}")

        # 获取 ConversationManager
        from capabilities.conversation.interface import IConversationManagerCapability
        conversation_manager = get_capability("conversation_manager", expected_type=IConversationManagerCapability)

        if conversation_manager:
            # 暂停任务并请求参数
            question = conversation_manager.pause_task_for_parameters(
                task_id=task_id,
                missing_params=missing_params,
                task_context={"collected_params": parameters},
                user_id="default_user"  # TODO: 从参数中获取user_id
            )

            # 发送暂停消息给AgentActor，AgentActor会转发给前台InteractionActor
            # 重要：包含ExecutionActor自己的地址，以便恢复时能找到
            pause_response = {
                "message_type": "task_paused",
                "task_id": task_id,
                "missing_params": missing_params,
                "question": question,
                "execution_actor_address": self.myAddress  # 添加ExecutionActor地址
            }

            self.send(reply_to, pause_response)

            # 发布任务暂停事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.TASK_PAUSED.value,
                source="ExecutionActor",
                agent_id="system",
                data={"missing_params": missing_params, "question": question}
            )
        else:
            # 如果没有ConversationManager，返回错误
            self._send_error(task_id, f"Missing required parameters: {', '.join(missing_params)}", reply_to)

    def _send_success(self, task_id: str, result: Any, reply_to: str) -> None:
        """发送成功结果"""
        response = {
            "type": "subtask_result",
            "task_id": task_id,
            "result": result
        }

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

    def _send_error(self, task_id: str, error: str, reply_to: str) -> None:
        """发送错误响应"""
        response = {
            "type": "subtask_error",
            "task_id": task_id,
            "error": error
        }

        self.send(reply_to, response)

        # 发布执行失败事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.CAPABILITY_FAILED.value,
            source="ExecutionActor",
            agent_id="system",
            data={"status": "failed", "error": error}
        )

        # 清理请求信息
        if task_id in self._pending_requests:
            del self._pending_requests[task_id]
