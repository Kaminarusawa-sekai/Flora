from .base import MessageBroker
from .redis_broker import RedisMessageBroker
from .rabbitmq_delayed import RabbitMQDelayedMessageBroker
from config.settings import settings


# 根据配置创建消息队列实例
def get_message_broker() -> MessageBroker:
    """
    根据配置获取消息队列实例
    上层调用者不需要知道具体实现类
    """
    if settings.message_broker_type == "redis":
        return RedisMessageBroker(settings.redis_url)
    elif settings.message_broker_type == "rabbitmq":
        return RabbitMQDelayedMessageBroker(settings.rabbitmq_url)
    else:
        raise ValueError(f"Unsupported message broker type: {settings.message_broker_type}")


# 提供一个全局实例，方便直接使用
message_broker = get_message_broker()


# 将基类、实现类和全局实例导出，方便上层导入
__all__ = [
    "MessageBroker",
    "RedisMessageBroker",
    "RabbitMQDelayedMessageBroker",
    "message_broker",
    "get_message_broker"
]