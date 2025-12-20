import logging
import threading
import json
from typing import Any

from message_queue_base import MessageQueueListener

# 尝试导入RabbitMQ依赖
try:
    import pika
    RABBITMQ_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to import RabbitMQ dependencies: {e}")
    RABBITMQ_AVAILABLE = False

# 导入消息相关模块
try:
    from common.messages.task_messages import AgentTaskMessage, ResumeTaskMessage
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to import message dependencies: {e}")
    AgentTaskMessage = None
    ResumeTaskMessage = None


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
        self.rabbitmq_url = self.config.get('rabbitmq_url', 'localhost')
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
            msg_type = data.get("msg_type")
            
            if msg_type == "START_TASK":
                # 构造 AgentTaskMessage
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
                    user_id=data['user_id']
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
            self.connection = pika.BlockingConnection(pika.ConnectionParameters(self.rabbitmq_url))
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue='agent_tasks', durable=True)
            
            self.logger.info(' [*] RabbitMQ监听已启动，等待消息. To exit press CTRL+C')
            self.channel.basic_consume(queue='agent_tasks', on_message_callback=self.callback)
            
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