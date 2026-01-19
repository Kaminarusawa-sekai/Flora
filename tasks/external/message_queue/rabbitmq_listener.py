import logging
import threading
import json
import time
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
from events.event_bus import event_bus
from common.event import EventType




class RabbitMQListenerImpl(MessageQueueListener):
    """
    RabbitMQ消息监听器实现类
    继承自MessageQueueListener抽象基类，实现RabbitMQ的具体监听逻辑

    支持两种模式：
    1. 传统模式：直接使用 actor_system + agent_actor_ref
    2. 路由模式：使用 TaskRouter 统一路由（推荐）
    """

    def __init__(
        self,
        actor_system: Any = None,
        agent_actor_ref: Any = None,
        config: dict = None,
        task_router: Any = None
    ):
        """
        初始化RabbitMQ监听器

        Args:
             actor_system: Actor系统实例（传统模式）
            agent_actor_ref: AgentActor的引用（传统模式）
            config: 配置参数字典，包含rabbitmq_url等配置
            task_router: TaskRouter实例（路由模式，推荐）
        """
        super().__init__(actor_system, agent_actor_ref, config)
        self.rabbitmq_url = self.config.get('rabbitmq_url', 'amqp://guest:guest@localhost:5672/')
        self.queue_name = self.config.get('queue_name', 'work.excute')
        self.connection = None
        self.channel = None
        self.thread = None
        self.running = False
        self.logger = logging.getLogger(__name__)

        # TaskRouter 模式
        self._task_router = task_router
        self._use_router = task_router is not None

    def set_task_router(self, task_router: Any) -> None:
        """
        设置 TaskRouter（可在初始化后设置）

        Args:
            task_router: TaskRouter 实例
        """
        self._task_router = task_router
        self._use_router = task_router is not None
        self.logger.info(f"TaskRouter set, use_router={self._use_router}")


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
            credentials=credentials,
            heartbeat=30,
            blocked_connection_timeout=300,
            socket_timeout=10,
            connection_attempts=3,
            retry_delay=2
        )

    def callback(self, ch, method, properties, body):
        """
        RabbitMQ消息回调函数
        """
        try:
            data = json.loads(body)
            msg_type = data.get("msg_type")
            # 确认消费
            ch.basic_ack(delivery_tag=method.delivery_tag)

            if msg_type == "START_TASK":
                # 从 schedule_meta 中提取额外信息
                schedule_meta = data.get("schedule_meta", {})
                input_params = schedule_meta.get("input_params", {})

                # 使用 task_id 作为 trace_id（如果没有单独的 trace_id）
                task_id = data.get('task_id', '')
                trace_id = data.get('trace_id', task_id)

                # 构造 AgentTaskMessage，补充必填字段
                # actor_msg = AgentTaskMessage(
                #     task_id=task_id,
                #     trace_id=trace_id,
                #     task_path="/",  # 根任务路径
                #     agent_id=schedule_meta.get("agent_id", "marketing"),
                #     content=data.get('user_input', ''),
                #     description=input_params.get('description', data.get('user_input', '')),
                #     user_id=data.get('user_id', 'system'),
                #     global_context={
                #         "schedule_meta": schedule_meta,
                #         "original_input": data.get('user_input', '')
                #     }
                # )
                # self.logger.info(f"投递新任务: {task_id}, trace_id: {trace_id}")
                # # 发布任务开始事件
                event_bus.publish_task_event(
                    task_id=task_id,
                    event_type=EventType.TASK_RUNNING.value,
                    trace_id=trace_id,
                    task_path="/",
                    source="RootActor",
                    agent_id=schedule_meta.get("agent_id", "marketing"),
                    user_id=data.get('user_id', 'system'),
                    name="营销",
                    data={
                        "task_spec": "",
                        "agent_id": schedule_meta.get("agent_id", "marketing"),
                        "merged_context": ""
                        },
                    enriched_context_snapshot=None,
                    )
                self._handle_start_task(data)

            elif msg_type == "RESUME_TASK":
                # task_id = data.get('task_id', '')
                # trace_id = data.get('trace_id', task_id)

                # # 构造 ResumeTaskMessage
                # actor_msg = ResumeTaskMessage(
                #     task_id=task_id,
                #     trace_id=trace_id,
                #     task_path=data.get('task_path', '/0'),
                #     parameters=data.get('parameters', {}),
                #     user_id=data.get('user_id', 'system')
                # )
                # self.logger.info(f"投递恢复指令: {task_id}")

                self._handle_resume_task(data)

            else:
                self.logger.warning(f"未知消息类型: {msg_type}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            

            

            # # 使用 tell() 发送给 Actor (非阻塞，发完即走)
            # self.actor_system.tell(self.agent_actor_ref, actor_msg)


            

        except Exception as e:
            self.logger.error(f"处理 RabbitMQ 消息时出错: {str(e)}", exc_info=True)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    def _handle_start_task(self, data: dict) -> None:
        """处理新任务消息"""
        # 从 schedule_meta 中提取额外信息
        schedule_meta = data.get("schedule_meta", {})
        input_params = schedule_meta.get("input_params", {})

        task_id = data.get('task_id', '')
        trace_id = data.get('trace_id', task_id)
        user_input = data.get('user_input', '')
        user_id = data.get('user_id', 'system')
        agent_id = schedule_meta.get("definition_id", "")

        self.logger.info(f"投递新任务: {task_id}, trace_id: {trace_id}")

        if self._use_router and self._task_router:
            # 使用 TaskRouterClient 模式（异步提交，不等待结果）
            self._task_router.submit_new_task(
                user_input=user_input,
                user_id=user_id,
                agent_id=agent_id if agent_id else None,
                task_id=task_id,
                trace_id=trace_id,
                task_path="/0",
                parameters=input_params,
                global_context={
                    "schedule_meta": schedule_meta,
                    "original_input": user_input
                },
                timeout=5.0  # 只等待任务被接受
            )
        else:
            # 传统模式：直接发送给 AgentActor
            from common.messages.task_messages import AgentTaskMessage

            actor_msg = AgentTaskMessage(
                task_id=task_id,
                trace_id=trace_id,
                task_path="/0",
                agent_id=agent_id or "DEFAULT_ROOT_AGENT",
                content=user_input,
                description=input_params.get('description', user_input),
                user_id=user_id,
                global_context={
                    "schedule_meta": schedule_meta,
                    "original_input": user_input
                }
            )
            self.actor_system.tell(self.agent_actor_ref, actor_msg)

    def _handle_resume_task(self, data: dict) -> None:
        """处理恢复任务消息"""
        task_id = data.get('task_id', '')
        trace_id = data.get('trace_id', task_id)
        task_path = data.get('task_path', '/0')
        parameters = data.get('parameters', {})
        user_id = data.get('user_id', 'system')

        self.logger.info(f"投递恢复指令: {task_id}")

        if self._use_router and self._task_router:
            # 使用 TaskRouterClient 模式（异步提交，不等待结果）
            self._task_router.submit_resume_task(
                trace_id=trace_id,
                parameters=parameters,
                user_id=user_id,
                timeout=5.0  # 只等待请求被接受
            )
        else:
            # 传统模式：直接发送给 AgentActor
            from common.messages.task_messages import ResumeTaskMessage

            actor_msg = ResumeTaskMessage(
                task_id=task_id,
                trace_id=trace_id,
                task_path=task_path,
                parameters=parameters,
                user_id=user_id
            )
            self.actor_system.tell(self.agent_actor_ref, actor_msg)

    def start(self):
        """
        启动RabbitMQ监听
        """
        if not RABBITMQ_AVAILABLE:
            self.logger.warning("RabbitMQ依赖未安装，跳过RabbitMQ监听")
            return

        while self.running:  # 控制是否继续重试
            try:
                self.logger.info("正在连接 RabbitMQ...")
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

                # 开始消费（会阻塞直到连接断开）
                self.channel.start_consuming()

            except pika.exceptions.AMQPConnectionError as e:
                self.logger.error(f"AMQP连接错误（可能网络问题）: {e}", exc_info=True)
            except pika.exceptions.StreamLostError as e:
                self.logger.error(f"连接丢失（如 ConnectionResetError）: {e}", exc_info=True)
            except Exception as e:
                self.logger.error(f"RabbitMQ监听异常: {e}", exc_info=True)
            finally:
                # 清理资源
                try:
                    if self.channel and self.channel.is_open:
                        self.channel.close()
                    if self.connection and self.connection.is_open:
                        self.connection.close()
                except Exception as cleanup_err:
                    self.logger.warning(f"清理连接时出错: {cleanup_err}")

            # 如果仍在运行状态，则等待后重试
            if self.running:
                self.logger.info("5秒后尝试重新连接 RabbitMQ...")
                time.sleep(5)

    def start_in_thread(self):
        """
        在独立线程中启动RabbitMQ监听
        """
        if not RABBITMQ_AVAILABLE:
            self.logger.warning("RabbitMQ依赖未安装，跳过RabbitMQ监听")
            return

        self.running = True
        self.thread = threading.Thread(target=self.start, daemon=True)
        self.thread.start()

    def stop(self):
        """
        停止RabbitMQ监听
        """
        self.running = False  # 先标记停止
        try:
            if self.channel:
                self.channel.stop_consuming()  # 触发 start_consuming() 退出
            if self.connection and self.connection.is_open:
                self.connection.close()
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=10.0)
            self.logger.info("RabbitMQ监听已停止")
        except Exception as e:
            self.logger.error(f"停止RabbitMQ监听时出错: {str(e)}", exc_info=True)