"""InteractionActor - 前台对话处理Actor

负责：
1. 作为系统唯一的前台入口
2. 使用ConversationManager处理所有对话逻辑
3. 判断是否需要转发给后台AgentActor
4. 处理后台返回的结果并与用户交互
"""

import logging
from typing import Any, Dict, Optional
from thespian.actors import Actor, ActorAddress

from capabilities.conversation.interface import IConversationManagerCapability
from capabilities import get_capability

from common.messages.interact_messages import (
    UserRequestMessage,
    InitConfigMessage,
    TaskPausedMessage,
    TaskResultMessage
)


logger = logging.getLogger("InteractionActor")


class InteractionActor(Actor):
    """
    前台交互Actor

    职责：
    - 接收用户输入
    - 通过ConversationManager判断意图和状态
    - 处理参数补充场景
    - 将需要执行的任务转发给后台AgentActor
    - 返回结果给用户
    """

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("InteractionActor")

        # 初始化ConversationManager
        self.conversation_manager: Optional[IConversationManagerCapability] = None

        # 后台AgentActor地址
        self.backend_addr: Optional[ActorAddress] = None

        # 用户连接映射: {user_id: connection_address}
        self.user_connections: Dict[str, ActorAddress] = {}

        # 任务ID到用户ID的映射
        self.task_to_user: Dict[str, str] = {}

        self.logger.info("InteractionActor created")

    def receiveMessage(self, message: Any, sender: ActorAddress):
        """接收并处理消息"""
        try:
            # 只处理对象类型消息
            if isinstance(message, InitConfigMessage):
                self._handle_init_config(message, sender)
            elif isinstance(message, UserRequestMessage):
                self._handle_user_input(message, sender)
            elif isinstance(message, TaskPausedMessage):
                self._handle_task_paused(message, sender)
            elif isinstance(message, TaskResultMessage):
                self._handle_task_result(message, sender)
            else:
                self.logger.warning(f"Unknown message format: {type(message)}")

        except Exception as e:
            self.logger.exception(f"Error in InteractionActor: {e}")
            # 向发送者返回错误
            self._send_error_to_user(sender, f"处理消息时发生错误: {str(e)}")

    def _handle_init_config(self, message: InitConfigMessage, sender: ActorAddress):
        """处理初始化配置"""
        self.backend_addr = message.backend_addr

        # 获取ConversationManager
        try:
            self.conversation_manager = get_capability(
                "conversation",
                expected_type=IConversationManagerCapability
            )
            if self.conversation_manager:
                self.conversation_manager.initialize()
                self.logger.info("✓ ConversationManager initialized successfully")
            else:
                self.logger.error("✗ Failed to get ConversationManager")
        except Exception as e:
            self.logger.error(f"✗ Failed to initialize ConversationManager: {e}")

        self.logger.info(f"✓ InteractionActor initialized with backend: {self.backend_addr}")

    def _handle_user_input(self, message: UserRequestMessage, sender: ActorAddress):
        """
        处理用户输入

        流程：
        1. 从message中提取user_input和user_id
        2. 调用ConversationManager.handle_user_input()
        3. 根据返回的action决定下一步操作
        """
        user_input = message.content
        user_id = message.user_id

        self.logger.info(f"[User {user_id}] Input: {user_input[:50]}...")

        # 记录用户连接
        self.user_connections[user_id] = sender

        # 确保ConversationManager已初始化
        if not self.conversation_manager:
            self.logger.error("ConversationManager not initialized")
            self._send_to_user(user_id, "系统尚未初始化，请稍后重试")
            return

        # 调用ConversationManager处理用户输入
        result = self.conversation_manager.handle_user_input(user_input, user_id)

        action = result.get("action")
        message_text = result.get("message")
        task_id = result.get("task_id")
        parameters = result.get("parameters", {})
        needs_backend = result.get("needs_backend", False)

        self.logger.info(f"[User {user_id}] Action: {action}, Needs Backend: {needs_backend}")

        # 根据action处理
        if not needs_backend:
            # 不需要后台处理，直接返回消息给用户
            self._send_to_user(user_id, message_text)
            return

        # 需要后台处理
        if action == "parameter_completion":
            # 参数补充完成，通知后台恢复任务
            self._resume_backend_task(task_id, parameters, user_id)
        elif action == "new_task":
            # 新任务，转发给后台
            self._forward_to_backend(user_input, user_id, task_id)
        else:
            # 其他需要后台处理的action
            self._forward_to_backend(user_input, user_id, task_id)

    def _handle_task_paused(self, message: TaskPausedMessage, sender: ActorAddress):
        """
        处理后台返回的任务暂停通知

        当后台ExecutionActor发现缺少参数时，会暂停任务并发送此消息
        """
        task_id = message.task_id
        missing_params = message.missing_params
        question = message.question

        self.logger.info(f"Task {task_id} paused, missing params: {missing_params}")

        # 找到对应的用户
        user_id = self.task_to_user.get(task_id, "default_user")

        # 向用户询问参数
        self._send_to_user(user_id, question)

    def _handle_task_result(self, message: TaskResultMessage, sender: ActorAddress):
        """处理后台返回的任务结果（合并完成和错误消息）"""
        task_id = message.task_id
        result = message.result
        error = message.error
        result_message = message.message or "任务已完成"

        # 找到对应的用户
        user_id = self.task_to_user.get(task_id, "default_user")

        if error:
            self.logger.error(f"Task {task_id} failed: {error}")
            # 返回错误给用户
            self._send_to_user(user_id, f"任务执行失败: {error}")
        else:
            self.logger.info(f"Task {task_id} completed")
            # 格式化结果返回给用户
            formatted_result = self._format_task_result(result, result_message)
            self._send_to_user(user_id, formatted_result)

        # 清理映射
        if task_id in self.task_to_user:
            del self.task_to_user[task_id]

    def _forward_to_backend(self, user_input: str, user_id: str, task_id: Optional[str] = None):
        """转发任务给后台AgentActor"""
        if not self.backend_addr:
            self.logger.error("Backend address not set!")
            self._send_to_user(user_id, "系统配置错误，后台服务未连接")
            return

        # 生成task_id（如果没有）
        if not task_id:
            import uuid
            task_id = f"task_{uuid.uuid4().hex[:12]}"

        # 记录任务到用户的映射
        self.task_to_user[task_id] = user_id


        # 构建转发消息
        backend_message = {
            "message_type": "agent_task",
            "task_id": task_id,
            "content": user_input,
            "description": user_input,
            "user_id": user_id,
            "reply_to": self.myAddress  # 让后台回复给InteractionActor
        }

        self.logger.info(f"Forwarding task {task_id} to backend for user {user_id}")

        # 先给用户一个确认消息
        self._send_to_user(user_id, "正在处理你的请求...")

        # 发送给后台
        self.send(self.backend_addr, backend_message)

    def _resume_backend_task(self, task_id: str, parameters: Dict[str, Any], user_id: str):
        """通知后台恢复暂停的任务"""
        if not self.backend_addr:
            self.logger.error("Backend address not set!")
            self._send_to_user(user_id, "系统配置错误，后台服务未连接")
            return

        # 构建恢复消息
        resume_message = {
            "message_type": "resume_task",
            "task_id": task_id,
            "parameters": parameters,
            "user_id": user_id,
            "reply_to": self.myAddress
        }

        self.logger.info(f"Resuming task {task_id} with parameters: {list(parameters.keys())}")

        # 发送给后台
        self.send(self.backend_addr, resume_message)

    def _send_to_user(self, user_id: str, message: str):
        """发送消息给用户"""
        user_addr = self.user_connections.get(user_id)
        if user_addr:
            response = {
                "type": "response",
                "user_id": user_id,
                "content": message,
                "timestamp": self._get_timestamp()
            }
            self.send(user_addr, response)
            self.logger.debug(f"Sent to user {user_id}: {message[:50]}...")
        else:
            self.logger.warning(f"User {user_id} connection not found")

    def _send_error_to_user(self, sender: ActorAddress, error_message: str):
        """发送错误消息"""
        response = {
            "type": "error",
            "content": error_message,
            "timestamp": self._get_timestamp()
        }
        self.send(sender, response)

    def _format_task_result(self, result: Any, message: str) -> str:
        """格式化任务结果"""
        # 简单实现：返回消息和结果
        if isinstance(result, dict) and "output" in result:
            return f"{message}\n\n结果：{result['output']}"
        elif isinstance(result, str):
            return f"{message}\n\n{result}"
        else:
            return message

    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
