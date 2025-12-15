import json
import os
from typing import Any, Callable, Optional

# 尝试导入aio_pika，若缺失则提供优雅的错误处理
try:
    import aio_pika
    HAS_AIO_PIKA = True
    
    # RabbitMQ配置
    RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    TASK_EVENT_TOPIC = os.getenv("TASK_EVENT_TOPIC", "tms.task.events")
    
    # MQ客户端实例
    mq_producer: Optional[aio_pika.RobustConnection] = None
    mq_consumer: Optional[aio_pika.RobustConnection] = None
    producer_channel: Optional[aio_pika.Channel] = None
    consumer_channel: Optional[aio_pika.Channel] = None
except ImportError:
    HAS_AIO_PIKA = False
    aio_pika = None
    mq_producer = None
    mq_consumer = None
    producer_channel = None
    consumer_channel = None
    RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    TASK_EVENT_TOPIC = os.getenv("TASK_EVENT_TOPIC", "tms.task.events")

async def init_mq():
    """
    初始化MQ连接
    
    Returns:
        bool: 初始化结果
    """
    if not HAS_AIO_PIKA:
        return False
    
    global mq_producer, mq_consumer, producer_channel, consumer_channel
    
    try:
        # 初始化生产者连接和通道
        mq_producer = await aio_pika.connect_robust(RABBITMQ_URL)
        producer_channel = await mq_producer.channel()
        
        # 初始化消费者连接和通道
        mq_consumer = await aio_pika.connect_robust(RABBITMQ_URL)
        consumer_channel = await mq_consumer.channel()
        
        # 声明队列（如果不存在）
        await consumer_channel.declare_queue(TASK_EVENT_TOPIC, durable=True)
        
        return True
    except Exception:
        return False

async def close_mq():
    """
    关闭MQ连接
    
    Returns:
        bool: 关闭结果
    """
    if not HAS_AIO_PIKA:
        return True
    
    global mq_producer, mq_consumer, producer_channel, consumer_channel
    
    try:
        if producer_channel:
            await producer_channel.close()
        if consumer_channel:
            await consumer_channel.close()
        if mq_producer:
            await mq_producer.close()
        if mq_consumer:
            await mq_consumer.close()
        
        return True
    except Exception:
        return False

async def publish_task_event(event: dict):
    """
    发布任务事件
    
    Args:
        event: 任务事件数据
        
    Returns:
        bool: 发布结果
    """
    if not HAS_AIO_PIKA:
        return False
    
    try:
        if not producer_channel:
            await init_mq()
        
        if producer_channel:
            message = aio_pika.Message(
                body=json.dumps(event).encode('utf-8'),
                content_type="application/json"
            )
            await producer_channel.default_exchange.publish(
                message,
                routing_key=TASK_EVENT_TOPIC
            )
            return True
        return False
    except Exception:
        return False

async def consume_task_events(callback: Callable[[dict], Any]):
    """
    消费任务事件
    
    Args:
        callback: 事件处理回调函数
    """
    if not HAS_AIO_PIKA:
        return
    
    try:
        if not consumer_channel:
            await init_mq()
        
        if consumer_channel:
            queue = await consumer_channel.declare_queue(TASK_EVENT_TOPIC, durable=True)
            
            async def on_message(message: aio_pika.IncomingMessage):
                async with message.process():
                    event = json.loads(message.body.decode('utf-8'))
                    await callback(event)
            
            await queue.consume(on_message)
    except Exception:
        pass

# 简化的事件发布函数
async def publish_started_event(task_id: str, trace_id: str, **kwargs):
    """
    发布任务开始事件
    
    Args:
        task_id: 任务ID
        trace_id: 跟踪ID
        **kwargs: 附加事件数据
    
    Returns:
        bool: 发布结果
    """
    event = {
        "event_type": "TASK_STARTED",
        "task_id": task_id,
        "trace_id": trace_id,
        "timestamp": json.dumps(kwargs.get("timestamp", json.loads(json.dumps(None)))),
        **kwargs
    }
    return await publish_task_event(event)

async def publish_completed_event(task_id: str, trace_id: str, **kwargs):
    """
    发布任务完成事件
    
    Args:
        task_id: 任务ID
        trace_id: 跟踪ID
        **kwargs: 附加事件数据
    
    Returns:
        bool: 发布结果
    """
    event = {
        "event_type": "TASK_COMPLETED",
        "task_id": task_id,
        "trace_id": trace_id,
        "timestamp": json.dumps(kwargs.get("timestamp", json.loads(json.dumps(None)))),
        **kwargs
    }
    return await publish_task_event(event)

async def publish_failed_event(task_id: str, trace_id: str, error: str, **kwargs):
    """
    发布任务失败事件
    
    Args:
        task_id: 任务ID
        trace_id: 跟踪ID
        error: 错误信息
        **kwargs: 附加事件数据
    
    Returns:
        bool: 发布结果
    """
    event = {
        "event_type": "TASK_FAILED",
        "task_id": task_id,
        "trace_id": trace_id,
        "error": error,
        "timestamp": json.dumps(kwargs.get("timestamp", json.loads(json.dumps(None)))),
        **kwargs
    }
    return await publish_task_event(event)
