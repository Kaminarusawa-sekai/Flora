import logging
import threading
import json
from typing import Any

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
        self.connection = None
        self.channel = None
        self.thread = None
        self.logger = logging.getLogger(__name__)
    
    def callback(self, ch, method, properties, body):
        """
        RabbitMQ消息回调函数
        """
        try:
            data = json.loads(body)
            msg_type = data.get("msg_type", "START_TASK")  # 默认使用START_TASK
            
            if msg_type == "START_TASK":
                # 处理START_TASK消息，支持两种格式：
                # 1. 新格式：直接包含instance_id、definition_id等字段
                # 2. 旧格式：包含task_id、user_input、user_id字段
                
                if 'instance_id' in data:  # 新格式（worker.execute消息）
                    instance_id = data['instance_id']
                    definition_id = data.get('definition_id')
                    trace_id = data.get('trace_id')
                    input_params = data.get('input_params', {})
                    
                    # 构造用户输入，适配AgentTaskMessage的格式
                    user_input = {
                        "instance_id": instance_id,
                        "definition_id": definition_id,
                        "trace_id": trace_id,
                        "input_params": input_params
                    }
                    
                    actor_msg = AgentTaskMessage(
                        task_id=instance_id,
                        user_input=user_input,
                        user_id=data.get('user_id', "system")  # 默认用户ID
                    )
                    self.logger.info(f"投递新任务: {instance_id}")
                else:  # 旧格式
                    actor_msg = AgentTaskMessage(
                        task_id=data['task_id'],
                        user_input=data['user_input'],
                        user_id=data['user_id']
                    )
                    self.logger.info(f"投递新任务: {data['task_id']}")
                
            elif msg_type == "RESUME_TASK":
                # 构造 ResumeTaskMessage
                actor_msg = ResumeTaskMessage(
                    task_id=data['task_id'],
                    parameters=data['parameters'],
                    user_id=data.get('user_id', "system")  # 默认用户ID
                )
                self.logger.info(f"投递恢复指令: {data['task_id']}")
            
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
            # RabbitMQ连接配置
            self.connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
            self.channel = self.connection.channel()
            # 只监听worker.execute队列
            queue_name = 'worker.execute'
            # 声明direct类型的exchange
            self.channel.exchange_declare(
                exchange=queue_name,
                type='direct',
                durable=True
            )
            # 声明队列
            self.channel.queue_declare(
                queue=queue_name,
                durable=True
            )
            # 将队列绑定到exchange
            self.channel.queue_bind(
                queue=queue_name,
                exchange=queue_name,
                routing_key=queue_name
            )
            
            self.logger.info(' [*] RabbitMQ监听已启动，等待消息. To exit press CTRL+C')
            self.channel.basic_consume(queue=queue_name, on_message_callback=self.callback)
            
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