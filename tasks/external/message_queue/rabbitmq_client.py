"""RabbitMQ客户端，用于发送延迟消息"""
import pika
import json
from typing import Dict, Any, Optional


class RabbitMQClient:
    """
    RabbitMQ客户端，用于发送延迟消息
    """
    
    def __init__(self, rabbitmq_url: str = "amqp://guest:guest@localhost:5672/"):
        """
        初始化RabbitMQ客户端
        
        Args:
            rabbitmq_url: RabbitMQ连接URL
        """
        self.rabbitmq_url = rabbitmq_url
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
    
    def close(self) -> None:
        """
        关闭RabbitMQ连接
        """
        if self._channel:
            self._channel.close()
        if self._connection:
            self._connection.close()
