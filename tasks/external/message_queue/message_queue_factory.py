import logging
from typing import Any, Optional

from .message_queue_base import MessageQueueListener

# 导入具体实现类

from .rabbitmq_listener import RabbitMQListenerImpl



class MessageQueueFactory:
    """
    消息队列工厂类，用于创建不同类型的消息队列监听器实例
    使用工厂模式，支持通过配置选择不同的消息队列实现
    """

    # 支持的消息队列类型映射
    _listener_classes = {
        'rabbitmq': RabbitMQListenerImpl
    }

    @staticmethod
    def create_listener(
        queue_type: str,
        actor_system: Any = None,
        agent_actor_ref: Any = None,
        config: dict = None,
        task_router: Any = None
    ) -> Optional[MessageQueueListener]:
        """
        创建消息队列监听器实例

        Args:
            queue_type: 消息队列类型，如 'rabbitmq'
            actor_system: Actor系统实例（传统模式）
            agent_actor_ref: AgentActor的引用（传统模式）
            config: 配置参数字典
            task_router: TaskRouter实例（路由模式，推荐）

        Returns:
            MessageQueueListener: 消息队列监听器实例
            None: 如果创建失败
        """
        logger = logging.getLogger(__name__)

        # 检查队列类型是否支持
        if queue_type not in MessageQueueFactory._listener_classes:
            logger.error(f"Unsupported message queue type: {queue_type}")
            return None

        listener_class = MessageQueueFactory._listener_classes[queue_type]

        # 检查实现类是否可用
        if listener_class is None:
            logger.error(f"Listener implementation for {queue_type} is not available")
            return None

        try:
            # 创建并返回监听器实例（支持 task_router 参数）
            return listener_class(
                actor_system=actor_system,
                agent_actor_ref=agent_actor_ref,
                config=config,
                task_router=task_router
            )
        except Exception as e:
            logger.error(f"Failed to create {queue_type} listener: {str(e)}", exc_info=True)
            return None

    @staticmethod
    def get_supported_types():
        """
        获取支持的消息队列类型列表

        Returns:
            list: 支持的消息队列类型列表
        """
        return list(MessageQueueFactory._listener_classes.keys())