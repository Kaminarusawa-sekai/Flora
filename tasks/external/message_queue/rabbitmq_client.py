"""RabbitMQ客户端，用于发送延迟消息和普通消息"""
import pika
import json
from typing import Dict, Any, Optional
from .message_queue_base import MessageQueuePublisher

# 从配置文件导入RabbitMQ URL
from config import RABBITMQ_URL


class RabbitMQClient(MessageQueuePublisher):
    """
    RabbitMQ客户端，用于发送延迟消息和普通消息
    实现了MessageQueuePublisher抽象基类
    """
    
    def __init__(self, rabbitmq_url: str = None, config: dict = None):
        """
        初始化RabbitMQ客户端
        
        Args:
            rabbitmq_url: RabbitMQ连接URL（默认使用配置文件中的RABBITMQ_URL）
            config: 配置参数字典
        """
        super().__init__(config)
        # 优先级：显式传入的rabbitmq_url > 配置字典中的rabbitmq_url > 配置文件中的RABBITMQ_URL
        self.rabbitmq_url = rabbitmq_url or self.config.get('rabbitmq_url', RABBITMQ_URL)
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.BlockingChannel] = None
    
    def connect(self) -> None:
        """
        建立RabbitMQ连接
        """
        self._connection = pika.BlockingConnection(pika.URLParameters(self.rabbitmq_url))
        self._channel = self._connection.channel()
        self._declare_exchanges_and_queues()
    
    def _declare_exchanges_and_queues(self) -> None:
        """
        声明交换机和队列
        """
        if not self._channel:
            raise ConnectionError("RabbitMQ channel not initialized")
        
        # 延迟交换器（需安装 rabbitmq-delayed-message-exchange 插件）
        self._channel.exchange_declare(
            exchange='loop_delay_exchange',
            exchange_type='x-delayed-message',
            arguments={'x-delayed-type': 'direct'}
        )
        
        # 触发队列
        self._channel.queue_declare(queue='loop_task_queue', durable=True)
        self._channel.queue_bind(
            queue='loop_task_queue',
            exchange='loop_delay_exchange',
            routing_key='loop_task'
        )
    
    def publish_delayed_task(self, task_id: str, delay_seconds: int, task_data: Optional[Dict[str, Any]] = None) -> None:
        """
        发布延迟任务
        
        Args:
            task_id: 任务ID
            delay_seconds: 延迟秒数
            task_data: 任务数据（可选）
        """
        if not self._channel:
            self.connect()
        
        # 构建消息体
        message_body = {
            "task_id": task_id,
            "task_data": task_data or {}
        }
        
        # 发送延迟消息
        self._channel.basic_publish(
            exchange='loop_delay_exchange',
            routing_key='loop_task',
            body=json.dumps(message_body),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 持久化消息
                headers={'x-delay': int(delay_seconds * 1000)}  # 延迟毫秒数
            )
        )
    
    def publish_to_queue(self, queue_name: str, message: Dict[str, Any], durable: bool = True) -> None:
        """
        普通发布消息到指定队列
        
        Args:
            queue_name: 目标队列名称
            message: 要发布的消息数据
            durable: 队列是否持久化（默认：True）
        """
        if not self._channel:
            self.connect()
        
        # 声明队列（幂等操作，已存在则忽略）
        self._channel.queue_declare(queue=queue_name, durable=durable)
        
        # 发布消息到默认交换机，使用队列名作为路由键
        self._channel.basic_publish(
            exchange='',  # 默认交换机
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(
                delivery_mode=2,  # 持久化消息
            )
        )
    
    def publish(self, message: Dict[str, Any], **kwargs):
        """
        发布消息到消息队列
        
        Args:
            message: 要发布的消息数据
            **kwargs: 额外的发布参数
                - queue_name: 目标队列名称（用于普通发布）
                - delay_seconds: 延迟秒数（用于延迟发布）
                - task_id: 任务ID（用于延迟发布）
                - durable: 队列是否持久化（默认：True）
        """
        if 'delay_seconds' in kwargs:
            # 延迟消息发布
            task_id = kwargs.get('task_id', message.get('task_id', str(id(message))))
            delay_seconds = kwargs['delay_seconds']
            self.publish_delayed_task(task_id, delay_seconds, message)
        elif 'queue_name' in kwargs:
            # 普通队列发布
            queue_name = kwargs['queue_name']
            durable = kwargs.get('durable', True)
            self.publish_to_queue(queue_name, message, durable)
        else:
            # 默认发布到loop_task_queue队列
            self.publish_to_queue('loop_task_queue', message)
    
    def close(self) -> None:
        """
        关闭RabbitMQ连接
        """
        if self._channel:
            self._channel.close()
        if self._connection:
            self._connection.close()
