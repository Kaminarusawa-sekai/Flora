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

from common.messages.task_messages import ExecuteTaskMessage, ExecutionResultMessage
from capabilities import get_capability
from capabilities.excution import BaseExecution
from capabilities.llm.interface import ILLMCapability
from capabilities.llm_memory.interface import IMemoryCapability
from events.event_bus import event_bus
from common.event import EventType

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
        self._excution:BaseExecution = get_capability("excution", BaseExecution)  # 添加连接器管理器实例
        self.logger.info("ExecutionActor initialized")
        self.task_id=None
        self.trace_id=None
        self.task_path=None
        self.reply_to=None
        self.global_context:Dict[str, Any] = {}
        self.enriched_context:Dict[str, Any] = {}

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
        running_config = msg.running_config or {}
        self.reply_to = msg.reply_to
        self.global_context = msg.global_context or {}
        self.enriched_context = msg.enriched_context or {}

        # 注意：不再使用 msg.params（已废弃）
        self._rewrite_running_config_with_memory(msg, running_config)
        self._execute(capability, self.task_id, running_config, self.reply_to)

    def _rewrite_running_config_with_memory(self, msg: ExecuteTaskMessage, running_config: Dict[str, Any]) -> None:
        user_id = running_config.get("user_id") or msg.user_id
        if not user_id:
            return
        text = running_config.get("description") or running_config.get("content")
        if not text:
            return
        rewritten = self._rewrite_with_memory(user_id, msg.task_path, text)
        if not rewritten or rewritten == text:
            return
        if "description" in running_config:
            running_config["description"] = rewritten
        if "content" in running_config:
            running_config["content"] = rewritten

    def _rewrite_with_memory(self, user_id: str, task_path: Optional[str], text: str) -> str:
        if not text:
            return text
        try:
            memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
        except Exception:
            return text
        scope = self._build_memory_scope(user_id, task_path, self.global_context)
        if not scope:
            return text
        try:
            memory_context = memory_cap.build_execution_context(scope, text)
        except Exception as e:
            self.logger.info(f"Memory read skipped: {e}")
            return text
        if not memory_context or memory_context.strip() == "无相关记忆可用。":
            return text
        try:
            llm = get_capability("llm", expected_type=ILLMCapability)
            prompt = (
                "你是任务语句补全器。根据记忆，将用户语句补全为可执行的明确指令。\n"
                "[记忆]\n"
                f"{memory_context}\n"
                "[原始语句]\n"
                f"{text}\n"
                "要求：\n"
                "1. 只输出补全后的语句\n"
                "2. 若无需补全，原样输出\n"
                "3. 不要解释\n"
            )
            rewritten = llm.generate(prompt, max_tokens=200, temperature=0.2)
            rewritten = rewritten.strip()
            if rewritten:
                self.logger.info(f"Rewritten execution task: {text} -> {rewritten}")
                return rewritten
        except Exception as e:
            self.logger.info(f"Rewrite skipped: {e}")
        return text

    @staticmethod
    def _build_memory_scope(user_id: str, task_path: Optional[str], global_context: Dict[str, Any]) -> str:
        if not user_id:
            return ""
        root_agent_id = global_context.get("root_agent_id")
        if not root_agent_id and task_path:
            parts = [part for part in task_path.split("/") if part]
            root_agent_id = parts[0] if parts else ""
        if root_agent_id:
            return f"{user_id}:{root_agent_id}"
        return user_id
    
    def _execute(self, capability: str, task_id: str, running_config: Dict[str, Any], reply_to: str) -> None:
        """
        执行任务的核心逻辑
        
        Args:
            capability: 能力名称
            task_id: 任务ID
            parameters: 参数
            reply_to: 回复地址
        """
        self.logger.info(f"⑪ 具体执行: task={task_id}, capability={capability}")

        # 保存请求信息（用于重试或调试）
        self._pending_requests[task_id] = {
            "capability": capability,
            "running_config": running_config,
            "reply_to": reply_to
        }

        # 发布执行开始事件
        event_bus.publish_task_event(
            task_id=task_id,
            trace_id=self.trace_id,
            task_path=self.task_path,
            event_type=EventType.CAPABILITY_EXECUTED.value,
            source="ExecutionActor",
            agent_id="excution",
            data={"capability": capability, "status": "started"}
        )

        # 根据能力类型分发
        if capability == "dify" or capability == "dify_workflow":
            self._execute_dify(task_id, running_config, reply_to)
        elif capability == "http" or capability.startswith("http_"):
            self._execute_http(task_id, running_config, reply_to)
        else:
            self._send_error(task_id, f"Capability {capability} not supported", reply_to)

    def _execute_dify(self, task_id: str, running_config: Dict[str, Any], reply_to: str) -> None:
        """
        执行 Dify 工作流
        """
        self.logger.info(f"Executing Dify workflow for task {task_id}")

        try:
            # 从 running_config 中提取必要参数
            api_key = running_config.get("api_key")
            inputs = running_config.get("inputs", {})
            agent_id = running_config.get("agent_id")
            user_id = running_config.get("user_id")
            content = running_config.get("content", "")
            description = running_config.get("description", "")

            if not api_key:
                raise ValueError("Missing 'api_key' in running_config for Dify execution")

            # 构造传递给 connector 的 params（保持与旧接口兼容）
            params = {
                "api_key": api_key,
                "inputs": inputs,
                "agent_id": agent_id,
                "user_id": user_id,
                "content": content,
                "description": description,
                # 如果 connector 需要上下文，可在此加入：
                "global_context": self.global_context,
                "enriched_context": self.enriched_context,
            }

            result = self._excution.execute(
                connector_name="dify",
                inputs=inputs,
                params=params
            )

            status = result.get("status")
            if status == "NEED_INPUT":
                missing_params = result["missing"]
                missing_params_descriptions = [str({"name": k, "description": v}) for k, v in missing_params.items()]
                completed_params = result["completed"]
                self._send_missing_parameters(task_id, missing_params_descriptions, completed_params, reply_to)
            elif status == "SUCCESS":
                self._send_success(task_id, result["result"], reply_to)
            elif status == "FAILURE":
                self._send_failure(task_id, result["error"], reply_to)
            elif status == "ERROR":
                self._send_error(task_id, result["error"], reply_to)
            else:
                self._send_error(task_id, f"Unknown status from connector: {status}", reply_to)

        except Exception as e:
            self.logger.exception(f"Dify execution failed: {e}")
            self._send_error(task_id, str(e), reply_to)

    def _execute_http(self, task_id: str, running_config: Dict[str, Any], reply_to: str) -> None:
        """
        执行 HTTP 请求

        running_config 应包含:
        - url: 完整的请求 URL
        - method: HTTP 方法 (GET/POST/PUT/DELETE)
        - headers: 请求头
        - args_schema: 参数 schema 列表（来自节点的 args 属性）
        - inputs: 输入参数
        - description: 任务描述（用于 LLM 提取参数）
        - content: 任务内容
        """
        self.logger.info(f"Executing HTTP request for task {task_id}")

        try:
            # 从 running_config 中提取 inputs
            inputs = running_config.get("inputs", {})

            # 执行 HTTP 请求
            result = self._excution.execute(
                connector_name="http",
                inputs=inputs,
                params=running_config  # 整个 running_config 作为 params 传入
            )

            # 检查返回状态
            status = result.get("status")

            if status == "NEED_INPUT":
                # 缺少必填参数
                missing = result.get("missing", {})
                completed = result.get("completed", {})
                # 将 missing dict 转换为描述列表
                missing_list = [f"{k}: {v}" for k, v in missing.items()] if isinstance(missing, dict) else missing
                self._send_missing_parameters(task_id, missing_list, completed, reply_to)
            elif status == "SUCCESS":
                self._send_success(task_id, result.get("result", result), reply_to)
            elif status == "ERROR":
                self._send_error(task_id, result.get("error", "Unknown error"), reply_to)
            else:
                # 没有明确状态，视为成功（兼容旧格式）
                exec_result = result.get("result", result)
                if isinstance(exec_result, dict) and exec_result.get("status") == "NEED_INPUT":
                    missing = exec_result.get("missing", {})
                    completed = exec_result.get("completed", {})
                    missing_list = [f"{k}: {v}" for k, v in missing.items()] if isinstance(missing, dict) else missing
                    self._send_missing_parameters(task_id, missing_list, completed, reply_to)
                else:
                    self._send_success(task_id, exec_result, reply_to)

        except Exception as e:
            self.logger.error(f"HTTP request failed: {e}")
            self._send_error(task_id, f"HTTP request failed: {str(e)}", reply_to)
    
    
    def _send_missing_parameters(self, task_id: str, missing_params: List[str],
                                   completed_params: Dict[str, Any], reply_to: str) -> None:
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
            result={
                "missing_params": missing_params,
                "completed_params": completed_params,
            },
            error=None,
            agent_id="system",
            missing_params=missing_params
        )
        
        self.send(reply_to, response)
        
        # 发布任务暂停事件
        event_bus.publish_task_event(
            task_id=task_id,
            trace_id=self.trace_id,
            task_path=self.task_path,
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
            trace_id=self.trace_id,
            task_path=self.task_path,
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
            trace_id=self.trace_id,
            task_path=self.task_path,
            event_type=EventType.CAPABILITY_ERROR.value,
            source="ExecutionActor",
            agent_id="system",
            data={"status": "failed", "error": error}
        )

        # 清理请求信息
        if task_id in self._pending_requests:
            del self._pending_requests[task_id]
