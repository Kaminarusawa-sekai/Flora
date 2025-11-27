# mcp_actor.py

from thespian.actors import Actor, ActorAddress
from typing import Any, Dict
import logging

# 假设这些是你已有的定义
from agent.message import (
    SubtaskResultMessage,
    MessageType,
    BaseMessage,
    SubtaskErrorMessage
)

# 假设你有一个函数调用大模型
from llm.qwen import QwenLLM  # 返回 JSON-serializable 结果


from agent.message import McpFallbackRequest



class McpLlmActor(Actor):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"McpLlmActor-{id(self)}")
        self.llm = QwenLLM()

    def receiveMessage(self, message, sender: ActorAddress):
        # 根据消息类型分发处理
        if isinstance(message, McpFallbackRequest):
            self._handle_mcp_fallback_request(message, sender)
        else:
            self.logger.warning(f"Received unknown message type: {type(message)} from {sender}")

    def _handle_mcp_fallback_request(self, msg: McpFallbackRequest, sender: ActorAddress):
        """
        接收兜底任务请求，调用大模型并返回结果。
        """
        task_id = msg.task_id
        context = msg.context

        self.logger.info(f"Handling fallback task {task_id} via LLM")

        try:
            # 调用大模型（同步调用）
            result = self.llm.generate(context)

            # 构造结果消息
            result_msg = SubtaskResultMessage(
                task_id=task_id,
                result=result
            )

            # 发送结果给发送者
            self.send(sender, result_msg)
            self.logger.info(f"Sent result for task {task_id} to {sender}")

        except Exception as e:
            self.logger.error(f"Error processing fallback task {task_id}: {e}", exc_info=True)
            # 发送错误消息
            self.send(sender, SubtaskErrorMessage(task_id=task_id, error=str(e)))
            # error_msg = SubtaskResultMessage(task_id=task_id, result=error_result)
            # self.send(reply_to, error_msg)