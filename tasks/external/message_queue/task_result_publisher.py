"""
任务结果发布器

将任务执行结果发布到 RabbitMQ，供 interaction 服务消费并推送给前端
"""
import logging
import json
import os
import time
from typing import Dict, Any, Optional
from datetime import datetime, timezone

try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError:
    RABBITMQ_AVAILABLE = False

logger = logging.getLogger(__name__)


class TaskResultPublisher:
    """
    任务结果发布器

    将任务结果发布到 work.result 队列，供 interaction 服务消费
    """

    # 默认队列名称（与 interaction 服务的 TaskResultListener 一致）
    DEFAULT_QUEUE_NAME = "work.result"

    def __init__(
        self,
        rabbitmq_url: Optional[str] = None,
        queue_name: str = DEFAULT_QUEUE_NAME
    ):
        """
        初始化任务结果发布器

        Args:
            rabbitmq_url: RabbitMQ 连接 URL
            queue_name: 队列名称
        """
        import config
        self.rabbitmq_url = rabbitmq_url or config.RABBITMQ_URL
        self.queue_name = queue_name
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel = None
        self._is_connected = False

    def connect(self) -> bool:
        """
        建立 RabbitMQ 连接

        Returns:
            bool: 是否连接成功
        """
        if not RABBITMQ_AVAILABLE:
            logger.warning("RabbitMQ (pika) not available")
            return False

        try:
            self._connection = pika.BlockingConnection(
                pika.URLParameters(self.rabbitmq_url)
            )
            self._channel = self._connection.channel()

            # 声明交换机和队列
            self._channel.exchange_declare(
                exchange=self.queue_name,
                exchange_type='direct',
                durable=True
            )
            self._channel.queue_declare(queue=self.queue_name, durable=True)
            self._channel.queue_bind(
                exchange=self.queue_name,
                queue=self.queue_name,
                routing_key=self.queue_name
            )

            self._is_connected = True
            logger.info(f"TaskResultPublisher connected to RabbitMQ, queue: {self.queue_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            self._is_connected = False
            return False

    def _ensure_connected(self) -> bool:
        """确保已连接"""
        if self._is_connected and self._connection and self._connection.is_open:
            return True
        return self.connect()

    def publish_result(
        self,
        trace_id: str,
        task_id: str,
        status: str,
        result: Any,
        error: Optional[str] = None,
        task_path: Optional[str] = None,
        user_id: Optional[str] = None,
        extra_data: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        retry_delay: int = 2
    ) -> bool:
        """
        发布任务结果

        Args:
            trace_id: 跟踪 ID（用于关联 session）
            task_id: 任务 ID
            status: 状态 (SUCCESS, FAILED, NEED_INPUT, ERROR)
            result: 任务结果
            error: 错误信息（可选）
            task_path: 任务路径（可选）
            user_id: 用户 ID（可选）
            extra_data: 额外数据（可选）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）

        Returns:
            bool: 是否发布成功
        """
        # 构建消息体
        message = {
            "trace_id": trace_id,
            "task_id": task_id,
            "status": status,
            "result": self._serialize_result(result),
            "error": error,
            "task_path": task_path,
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # 合并额外数据
        if extra_data:
            message.update(extra_data)

        for attempt in range(max_retries + 1):
            # 尝试确保连接
            if not self._ensure_connected():
                if attempt < max_retries:
                    logger.warning(
                        f"RabbitMQ connection failed (attempt {attempt + 1}/{max_retries + 1}), "
                        f"retrying in {retry_delay}s..."
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error("Failed to connect to RabbitMQ after retries. Message lost.")
                    return False

            try:
                # 发布消息
                self._channel.basic_publish(
                    exchange=self.queue_name,
                    routing_key=self.queue_name,
                    body=json.dumps(message, ensure_ascii=False, default=str),
                    properties=pika.BasicProperties(
                        delivery_mode=2,  # 持久化消息
                        content_type='application/json'
                    )
                )

                logger.info(f"Published task result: trace_id={trace_id}, status={status}")
                return True

            except Exception as e:
                logger.error(f"Failed to publish task result (attempt {attempt + 1}/{max_retries + 1}): {e}")
                self._is_connected = False
                if attempt < max_retries:
                    logger.warning(f"Retrying in {retry_delay}s...")
                    time.sleep(retry_delay)
                else:
                    logger.error("Failed to publish task result after retries. Message lost.")
                    return False

    def publish_need_input(
        self,
        trace_id: str,
        task_id: str,
        missing_params: list,
        message: str = "请补充缺失的参数",
        task_path: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        发布需要输入的状态

        Args:
            trace_id: 跟踪 ID
            task_id: 任务 ID
            missing_params: 缺失的参数列表
            message: 提示消息
            task_path: 任务路径
            user_id: 用户 ID

        Returns:
            bool: 是否发布成功
        """
        return self.publish_result(
            trace_id=trace_id,
            task_id=task_id,
            status="NEED_INPUT",
            result={
                "missing_params": missing_params,
                "message": message
            },
            task_path=task_path,
            user_id=user_id
        )

    def publish_success(
        self,
        trace_id: str,
        task_id: str,
        result: Any,
        task_path: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        发布成功结果

        Args:
            trace_id: 跟踪 ID
            task_id: 任务 ID
            result: 任务结果
            task_path: 任务路径
            user_id: 用户 ID

        Returns:
            bool: 是否发布成功
        """
        return self.publish_result(
            trace_id=trace_id,
            task_id=task_id,
            status="SUCCESS",
            result=result,
            task_path=task_path,
            user_id=user_id
        )

    def publish_failed(
        self,
        trace_id: str,
        task_id: str,
        error: str,
        result: Any = None,
        task_path: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> bool:
        """
        发布失败结果

        Args:
            trace_id: 跟踪 ID
            task_id: 任务 ID
            error: 错误信息
            result: 任务结果（可选）
            task_path: 任务路径
            user_id: 用户 ID

        Returns:
            bool: 是否发布成功
        """
        return self.publish_result(
            trace_id=trace_id,
            task_id=task_id,
            status="FAILED",
            result=result,
            error=error,
            task_path=task_path,
            user_id=user_id
        )

    def _serialize_result(self, result: Any) -> Any:
        """
        序列化结果（处理不可 JSON 序列化的对象）
        """
        if result is None:
            return None

        if isinstance(result, (str, int, float, bool)):
            return result

        if isinstance(result, dict):
            return {k: self._serialize_result(v) for k, v in result.items()}

        if isinstance(result, (list, tuple)):
            return [self._serialize_result(item) for item in result]

        # 尝试转换为字典
        if hasattr(result, 'to_dict'):
            return result.to_dict()
        if hasattr(result, 'model_dump'):
            return result.model_dump()
        if hasattr(result, '__dict__'):
            return {k: self._serialize_result(v) for k, v in result.__dict__.items()
                    if not k.startswith('_')}

        # 最后尝试转为字符串
        return str(result)

    def close(self) -> None:
        """关闭连接"""
        try:
            if self._channel:
                self._channel.close()
            if self._connection:
                self._connection.close()
            self._is_connected = False
            logger.info("TaskResultPublisher connection closed")
        except Exception as e:
            logger.error(f"Error closing TaskResultPublisher: {e}")


# 单例实例
_publisher: Optional[TaskResultPublisher] = None


def get_task_result_publisher() -> TaskResultPublisher:
    """获取任务结果发布器单例"""
    global _publisher
    if _publisher is None:
        _publisher = TaskResultPublisher()
    return _publisher


def init_task_result_publisher(
    rabbitmq_url: Optional[str] = None,
    queue_name: str = TaskResultPublisher.DEFAULT_QUEUE_NAME
) -> TaskResultPublisher:
    """
    初始化任务结果发布器

    Args:
        rabbitmq_url: RabbitMQ 连接 URL
        queue_name: 队列名称

    Returns:
        TaskResultPublisher 实例
    """
    global _publisher
    _publisher = TaskResultPublisher(rabbitmq_url=rabbitmq_url, queue_name=queue_name)
    _publisher.connect()
    return _publisher
