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
import requests

from capabilities import get_capability
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
                elif msg_type == "dify_schema_response":
                    # Dify Schema 响应
                    self._handle_dify_schema_response(msg, sender)
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
        parameters = msg.get("parameters", {})
        reply_to = msg.get("reply_to", sender)

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
        步骤：
        1. 先获取 Dify Schema（如果需要）
        2. 补充参数
        3. 执行工作流

        Args:
            task_id: 任务ID
            parameters: 参数
            reply_to: 回复地址
        """
        self.logger.info(f"Executing Dify workflow for task {task_id}")

        try:
            # 检查是否需要先获取Schema
            if parameters.get("needs_schema", False):
                # 先获取Schema
                self._fetch_dify_schema(task_id, parameters, reply_to)
            else:
                # 直接执行
                self._execute_dify_workflow(task_id, parameters, reply_to)

        except Exception as e:
            self.logger.error(f"Dify execution failed: {e}")
            self._send_error(task_id, str(e), reply_to)

    def _fetch_dify_schema(self, task_id: str, parameters: Dict[str, Any], reply_to: str) -> None:
        """
        获取 Dify Schema

        Args:
            task_id: 任务ID
            parameters: 参数
            reply_to: 回复地址
        """
        api_key = parameters.get("api_key")
        base_url = parameters.get("base_url")
        workflow_id = parameters.get("workflow_id")

        if not all([api_key, base_url, workflow_id]):
            self._send_error(task_id, "Missing required parameters for Dify", reply_to)
            return

        try:
            # 调用Dify API获取Schema
            url = f"{base_url}/v1/workflows/{workflow_id}/parameters"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }

            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()

            schema = response.json()

            # 更新参数中的 schema 信息
            self._pending_requests[task_id]["schema"] = schema

            # 现在执行工作流
            self._execute_dify_workflow(task_id, parameters, reply_to)

        except Exception as e:
            self.logger.error(f"Failed to fetch Dify schema: {e}")
            self._send_error(task_id, f"Failed to fetch Dify schema: {str(e)}", reply_to)

    def _execute_dify_workflow(self, task_id: str, parameters: Dict[str, Any], reply_to: str) -> None:
        """
        执行 Dify 工作流

        Args:
            task_id: 任务ID
            parameters: 参数
            reply_to: 回复地址
        """
        # 检查必需参数
        required_params = ["api_key", "base_url", "workflow_id"]
        missing_params = self._check_missing_parameters(required_params, parameters)

        if missing_params:
            # 请求补充参数
            self._request_missing_parameters(task_id, missing_params, parameters, reply_to)
            return

        api_key = parameters.get("api_key")
        base_url = parameters.get("base_url")
        workflow_id = parameters.get("workflow_id")
        inputs = parameters.get("inputs", {})
        user = parameters.get("user", "default_user")

        try:
            # 调用Dify API执行工作流
            url = f"{base_url}/v1/workflows/run"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "inputs": inputs,
                "response_mode": "blocking",
                "user": user
            }

            response = requests.post(url, json=payload, headers=headers, timeout=120)
            response.raise_for_status()

            result = response.json()

            # 发送成功结果
            self._send_success(task_id, result, reply_to)

        except Exception as e:
            self.logger.error(f"Dify workflow execution failed: {e}")
            self._send_error(task_id, f"Dify execution failed: {str(e)}", reply_to)

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
            # 检查必需参数
            required_params = ["url"]
            missing_params = self._check_missing_parameters(required_params, parameters)

            if missing_params:
                # 请求补充参数
                self._request_missing_parameters(task_id, missing_params, parameters, reply_to)
                return

            url = parameters.get("url")
            method = parameters.get("method", "GET").upper()
            headers = parameters.get("headers", {})
            data = parameters.get("data")
            timeout = parameters.get("timeout", 30)

            # 发送HTTP请求
            if method == "GET":
                response = requests.get(url, headers=headers, params=data, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=timeout)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=timeout)
            else:
                self._send_error(task_id, f"Unsupported HTTP method: {method}", reply_to)
                return

            response.raise_for_status()

            # 尝试解析JSON，如果失败则返回文本
            try:
                result = response.json()
            except:
                result = {"text": response.text, "status_code": response.status_code}

            self._send_success(task_id, result, reply_to)

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
            from capability_actors.data_actor import DataActor

            # 创建 DataActor
            data_actor = self.createActor(DataActor)

            # 构建查询请求
            query_msg = {
                "type": "query",
                "task_id": task_id,
                "query": parameters.get("query"),
                "params": parameters.get("params", {}),
                "reply_to": reply_to
            }

            # 发送查询请求
            self.send(data_actor, query_msg)

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

    def _check_missing_parameters(self, required_params: List[str],
                                  parameters: Dict[str, Any]) -> List[str]:
        """
        检查缺失的参数

        Args:
            required_params: 必需参数列表
            parameters: 当前参数字典

        Returns:
            缺失的参数列表
        """
        missing = []
        for param in required_params:
            if param not in parameters or parameters[param] is None or parameters[param] == "":
                missing.append(param)
        return missing

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
        from capabilities.context.conversation_manager import IConversationManagerCapability
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

    def _handle_dify_schema_response(self, msg: Dict[str, Any], sender: str) -> None:
        """处理 Dify Schema 响应"""
        task_id = msg.get("task_id")
        schema = msg.get("schema")

        if task_id in self._pending_requests:
            req_info = self._pending_requests[task_id]
            req_info["schema"] = schema

            # 继续执行工作流
            self._execute_dify_workflow(task_id, req_info["parameters"], req_info["reply_to"])

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
