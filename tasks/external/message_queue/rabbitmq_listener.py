import logging
import threading
import json
from typing import Any
from urllib.parse import urlparse

from .message_queue_base import MessageQueueListener

# 尝试导入RabbitMQ依赖
try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to import RabbitMQ dependencies: {e}")
    RABBITMQ_AVAILABLE = False

# 导入消息相关模块

from common.messages.task_messages import AgentTaskMessage, ResumeTaskMessage




class RabbitMQListenerImpl(MessageQueueListener):
    """
    RabbitMQ消息监听器实现类
    继承自MessageQueueListener抽象基类，实现RabbitMQ的具体监听逻辑
    """

    def __init__(self, actor_system: Any, agent_actor_ref: Any, config: dict = None):
        """
        初始化RabbitMQ监听器

        Args:
            actor_system: Actor系统实例
            agent_actor_ref: AgentActor的引用
            config: 配置参数字典，包含rabbitmq_url等配置
        """
        super().__init__(actor_system, agent_actor_ref, config)
        self.rabbitmq_url = self.config.get('rabbitmq_url', 'amqp://guest:guest@localhost:5672/')
        self.queue_name = self.config.get('queue_name', 'work.excute')
        self.connection = None
        self.channel = None
        self.thread = None
        self.logger = logging.getLogger(__name__)

    def _parse_rabbitmq_url(self):
        """解析 RabbitMQ URL 为 pika 连接参数"""
        parsed = urlparse(self.rabbitmq_url)

        # 解码密码中的特殊字符
        from urllib.parse import unquote
        password = unquote(parsed.password) if parsed.password else 'guest'

        credentials = pika.PlainCredentials(
            username=parsed.username or 'guest',
            password=password
        )

        return pika.ConnectionParameters(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5672,
            virtual_host=parsed.path.lstrip('/') or '/',
            credentials=credentials
        )

    def callback(self, ch, method, properties, body):
        """
        RabbitMQ消息回调函数
        """
        try:
            data = json.loads(body)
            msg_type = data.get("msg_type")

            if msg_type == "START_TASK":
                # 从 schedule_meta 中提取额外信息
                schedule_meta = data.get("schedule_meta", {})
                input_params = schedule_meta.get("input_params", {})

                # 使用 task_id 作为 trace_id（如果没有单独的 trace_id）
                task_id = data.get('task_id', '')
                trace_id = data.get('trace_id', task_id)

                # 构造 AgentTaskMessage，补充必填字段
                actor_msg = AgentTaskMessage(
                    task_id=task_id,
                    trace_id=trace_id,
                    task_path="/",  # 根任务路径
                    agent_id=schedule_meta.get("agent_id", "marketing"),
                    content=data.get('user_input', ''),
                    description=input_params.get('description', data.get('user_input', '')),
                    user_id=data.get('user_id', 'system'),
                    global_context={
                        "schedule_meta": schedule_meta,
                        "original_input": data.get('user_input', '')
                    }
                )
                self.logger.info(f"投递新任务: {task_id}, trace_id: {trace_id}")

            elif msg_type == "RESUME_TASK":
                task_id = data.get('task_id', '')
                trace_id = data.get('trace_id', task_id)

                # 构造 ResumeTaskMessage
                actor_msg = ResumeTaskMessage(
                    task_id=task_id,
                    trace_id=trace_id,
                    task_path=data.get('task_path', '/0'),
                    parameters=data.get('parameters', {}),
                    user_id=data.get('user_id', 'system')
                )
                self.logger.info(f"投递恢复指令: {task_id}")

            else:
                self.logger.warning(f"未知消息类型: {msg_type}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            # 使用 tell() 发送给 Actor (非阻塞，发完即走)
            self.actor_system.tell(self.agent_actor_ref, actor_msg)

            # 确认消费
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            self.logger.error(f"处理 RabbitMQ 消息时出错: {str(e)}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    def start(self):
        """
        启动RabbitMQ监听
        """
        if not RABBITMQ_AVAILABLE:
            self.logger.warning("RabbitMQ依赖未安装，跳过RabbitMQ监听")
            return

        try:
            # 使用解析后的连接参数
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

            self.logger.info(f' [*] RabbitMQ监听已启动，队列: {self.queue_name}，等待消息...')
            self.channel.basic_consume(queue=self.queue_name, on_message_callback=self.callback)

            self.running = True
            self.channel.start_consuming()

        except Exception as e:
            self.logger.error(f"RabbitMQ连接出错: {str(e)}", exc_info=True)
            self.running = False

    def start_in_thread(self):
        """
        在独立线程中启动RabbitMQ监听
        """
        if not RABBITMQ_AVAILABLE:
            self.logger.warning("RabbitMQ依赖未安装，跳过RabbitMQ监听")
            return

        self.thread = threading.Thread(target=self.start, daemon=True)
        self.thread.start()

    def stop(self):
        """
        停止RabbitMQ监听
        """
        if not self.running:
            return

        try:
            if self.channel:
                self.channel.stop_consuming()
            if self.connection:
                self.connection.close()
            self.running = False
            if self.thread:
                self.thread.join(timeout=5.0)
            self.logger.info("RabbitMQ监听已停止")
        except Exception as e:
            self.logger.error(f"停止RabbitMQ监听时出错: {str(e)}", exc_info=True)