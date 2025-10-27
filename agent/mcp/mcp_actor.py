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


class McpFallbackRequest(BaseMessage):
    """MCP Actor 接收的任务请求消息"""
    message_type: MessageType = MessageType.MCP_FALLBACK_REQUEST
    task_id: str
    context: Dict[str, Any]
    reply_to: ActorAddress  # 谁需要接收 SubtaskResultMessage


class McpLlmActor(Actor):
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"McpLlmActor-{id(self)}")
        self.llm = QwenLLM()

    def receiveMsg_McpFallbackRequest(self, msg: McpFallbackRequest, sender: ActorAddress):
        """
        接收兜底任务请求，调用大模型并返回结果。
        """
        task_id = msg.task_id
        context = msg.context
        reply_to = msg.reply_to

        self.logger.info(f"Handling fallback task {task_id} via LLM")

        try:
            # 调用大模型（同步调用，Thespian 允许在 receiveMsg 中做 I/O，但不要长时间阻塞）
            result = self.llm.generate(context)

            # 构造结果消息
            result_msg = SubtaskResultMessage(
                task_id=task_id,
                result=result
            )

            # 发送结果给指定接收者（通常是任务协调者）
            self.send(reply_to, result_msg)
            self.logger.info(f"Sent result for task {task_id} to {reply_to}")

        except Exception as e:
            self.logger.error(f"Error processing fallback task {task_id}: {e}", exc_info=True)
            # 可选：发送错误结果或空结果
            error_result = {"error": str(e)}
            self.send(sender, SubtaskErrorMessage(task_id, error_result))
            # error_msg = SubtaskResultMessage(task_id=task_id, result=error_result)
            # self.send(reply_to, error_msg)