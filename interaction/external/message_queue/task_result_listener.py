"""
任务结果监听器

监听 RabbitMQ 队列，接收任务执行结果，并：
1. 根据 trace_id 找到对应的 session_id
2. 将任务结果存储到对话历史
3. 通过 SSE 推送通知前端
"""
import logging
import threading
import json
import asyncio
from typing import Any, Callable, Optional
from urllib.parse import urlparse, unquote
from datetime import datetime, timezone

# 尝试导入 RabbitMQ 依赖
try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError as e:
    RABBITMQ_AVAILABLE = False

logger = logging.getLogger(__name__)


class TaskResultListener:
    """
    任务结果监听器

    监听 task.result 队列，处理任务执行结果
    """

    def __init__(
        self,
        rabbitmq_url: str = 'amqp://guest:guest@localhost:5672/',
        queue_name: str = 'task.result',
        on_result_callback: Optional[Callable[[dict], None]] = None
    ):
        """
        初始化任务结果监听器

        Args:
            rabbitmq_url: RabbitMQ 连接 URL
            queue_name: 监听的队列名称
            on_result_callback: 收到结果时的回调函数
        """
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.on_result_callback = on_result_callback

        self.connection = None
        self.channel = None
        self.thread = None
        self.running = False

    def _parse_rabbitmq_url(self):
        """解析 RabbitMQ URL 为 pika 连接参数"""
        parsed = urlparse(self.rabbitmq_url)

        password = unquote(parsed.password) if parsed.password else 'guest'

        credentials = pika.PlainCredentials(
            username=parsed.username or 'guest',
            password=password
        )

        return pika.ConnectionParameters(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5672,
            virtual_host=parsed.path.lstrip('/') or '/',
            credentials=credentials,
            heartbeat=600,
            blocked_connection_timeout=300
        )

    def _callback(self, ch, method, properties, body):
        """
        RabbitMQ 消息回调函数

        消息格式：
        {
            "trace_id": "xxx",
            "status": "SUCCESS" | "FAILED",
            "result": "任务结果文本",
            "error": "错误信息（可选）"
        }
        """
        try:
            data = json.loads(body)
            trace_id = data.get("trace_id")
            status = data.get("status", "UNKNOWN")
            result = data.get("result", "")
            error = data.get("error")

            logger.info(f"Received task result: trace_id={trace_id}, status={status}")

            if not trace_id:
                logger.warning("Received task result without trace_id, ignoring")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # 调用回调函数处理结果
            if self.on_result_callback:
                try:
                    self.on_result_callback({
                        "trace_id": trace_id,
                        "status": status,
                        "result": result,
                        "error": error,
                        "received_at": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as e:
                    logger.error(f"Error in result callback: {e}", exc_info=True)

            # 确认消息
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task result message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
        except Exception as e:
            logger.error(f"Error processing task result: {e}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start(self):
        """启动监听器（阻塞）"""
        if not RABBITMQ_AVAILABLE:
            logger.warning("RabbitMQ (pika) not available, task result listener disabled")
            return

        try:
            connection_params = self._parse_rabbitmq_url()
            self.connection = pika.BlockingConnection(connection_params)
            self.channel = self.connection.channel()

            # 声明交换机和队列
            self.channel.exchange_declare(
                exchange=self.queue_name,
                exchange_type='direct',
                durable=True
            )
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            self.channel.queue_bind(
                exchange=self.queue_name,
                queue=self.queue_name,
                routing_key=self.queue_name
            )

            # 设置 QoS
            self.channel.basic_qos(prefetch_count=10)

            logger.info(f"Task result listener started, queue: {self.queue_name}")

            self.running = True
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self._callback
            )
            self.channel.start_consuming()

        except Exception as e:
            logger.error(f"Failed to start task result listener: {e}", exc_info=True)
            self.running = False

    def start_in_thread(self):
        """在独立线程中启动监听器"""
        if not RABBITMQ_AVAILABLE:
            logger.warning("RabbitMQ (pika) not available, task result listener disabled")
            return

        self.thread = threading.Thread(target=self.start, daemon=True)
        self.thread.start()
        logger.info("Task result listener thread started")

    def stop(self):
        """停止监听器"""
        if not self.running:
            return

        try:
            self.running = False
            if self.channel:
                self.channel.stop_consuming()
            if self.connection:
                self.connection.close()
            if self.thread:
                self.thread.join(timeout=5.0)
            logger.info("Task result listener stopped")
        except Exception as e:
            logger.error(f"Error stopping task result listener: {e}", exc_info=True)
