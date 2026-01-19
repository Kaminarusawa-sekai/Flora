"""
任务结果处理服务

处理从 RabbitMQ 接收到的任务结果：
1. 根据 trace_id 查找对应的 session_id
2. 将结果存储到对话历史
3. 通过 SSE 推送给前端
"""
import logging
import json
import asyncio
from typing import Dict, Any, Optional, Callable
from datetime import datetime, timezone

from external.database.dialog_state_repo import DialogStateRepository

logger = logging.getLogger(__name__)


class TaskResultHandler:
    """
    任务结果处理器

    负责处理任务执行结果，更新对话状态并推送 SSE 事件
    """

    def __init__(
        self,
        dialog_repo: DialogStateRepository,
        session_queues: Dict[str, asyncio.Queue],
        event_loop: Optional[asyncio.AbstractEventLoop] = None
    ):
        """
        初始化任务结果处理器

        Args:
            dialog_repo: 对话状态仓库
            session_queues: 会话级别的 SSE 事件队列（来自 api_server.py 的 SESSION_QUEUES）
            event_loop: 异步事件循环（用于在同步回调中调度异步任务）
        """
        self.dialog_repo = dialog_repo
        self.session_queues = session_queues
        self.event_loop = event_loop

    def handle_task_result(self, result: Dict[str, Any]) -> None:
        """
        处理任务结果（同步方法，供 RabbitMQ 回调使用）

        Args:
            result: 任务结果，格式：
                {
                    "trace_id": "xxx",
                    "status": "SUCCESS" | "FAILED",
                    "result": "任务结果文本",
                    "error": "错误信息（可选）",
                    "received_at": "ISO时间戳"
                }
        """
        trace_id = result.get("trace_id")
        if not trace_id:
            logger.warning("Task result missing trace_id")
            return

        # 1. 根据 trace_id 查找 session_id
        session_id = self.dialog_repo.get_session_by_trace(trace_id)
        if not session_id:
            logger.warning(f"No session found for trace_id: {trace_id}")
            return

        logger.info(f"Processing task result for trace_id={trace_id}, session_id={session_id}")

        # 2. 获取完整的映射信息（包含 user_id）
        mapping = self.dialog_repo.get_trace_mapping(trace_id)
        user_id = mapping.get("user_id") if mapping else None

        # 3. 构建 SSE 事件
        status = result.get("status", "UNKNOWN")
        task_result = result.get("result", "")
        error = result.get("error")

        sse_event = {
            "event": "task_result",
            "data": json.dumps({
                "trace_id": trace_id,
                "status": status,
                "result": task_result,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, ensure_ascii=False)
        }

        # 4. 推送 SSE 事件到对应的 session 队列
        if session_id in self.session_queues:
            try:
                if self.event_loop and self.event_loop.is_running():
                    # 在异步事件循环中调度
                    asyncio.run_coroutine_threadsafe(
                        self._push_to_queue(session_id, sse_event),
                        self.event_loop
                    )
                else:
                    # 尝试直接放入队列（如果队列支持线程安全操作）
                    self.session_queues[session_id].put_nowait(sse_event)
                logger.info(f"Pushed task result to SSE queue for session: {session_id}")
            except Exception as e:
                logger.error(f"Failed to push SSE event: {e}")
        else:
            logger.debug(f"No active SSE connection for session: {session_id}")

        # 5. 更新对话状态（可选：将任务结果添加到对话历史）
        self._update_dialog_state(session_id, trace_id, status, task_result, error)

    async def _push_to_queue(self, session_id: str, event: Dict[str, Any]) -> None:
        """异步推送事件到队列"""
        await self.session_queues[session_id].put(event)

    def _update_dialog_state(
        self,
        session_id: str,
        trace_id: str,
        status: str,
        result: str,
        error: Optional[str]
    ) -> None:
        """
        更新对话状态

        将任务结果记录到对话状态中
        """
        try:
            dialog_state = self.dialog_repo.get_dialog_state(session_id)
            if not dialog_state:
                logger.warning(f"Dialog state not found for session: {session_id}")
                return

            # 更新 active_task_execution 状态
            # 如果当前活跃任务就是这个 trace_id，则清除
            if dialog_state.active_task_execution:
                # 任务已完成，可以清除活跃任务标记
                # 注意：这里可能需要更复杂的逻辑来判断是否清除
                pass

            # 更新 last_updated
            dialog_state.last_updated = datetime.now(timezone.utc)

            # 保存更新
            self.dialog_repo.update_dialog_state(dialog_state)

            logger.debug(f"Updated dialog state for session: {session_id}")

        except Exception as e:
            logger.error(f"Failed to update dialog state: {e}", exc_info=True)


# 全局单例
_task_result_handler: Optional[TaskResultHandler] = None


def get_task_result_handler() -> Optional[TaskResultHandler]:
    """获取任务结果处理器单例"""
    return _task_result_handler


def init_task_result_handler(
    dialog_repo: DialogStateRepository,
    session_queues: Dict[str, asyncio.Queue],
    event_loop: Optional[asyncio.AbstractEventLoop] = None
) -> TaskResultHandler:
    """
    初始化任务结果处理器

    Args:
        dialog_repo: 对话状态仓库
        session_queues: 会话级别的 SSE 事件队列
        event_loop: 异步事件循环

    Returns:
        TaskResultHandler 实例
    """
    global _task_result_handler
    _task_result_handler = TaskResultHandler(
        dialog_repo=dialog_repo,
        session_queues=session_queues,
        event_loop=event_loop
    )
    return _task_result_handler
