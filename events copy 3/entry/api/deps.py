from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends
from ...config.settings import settings
from ...external.cache.redis_impl import RedisCacheClient
from ...external.messaging.rabbitmq_delayed import RabbitMQDelayedMessageBroker
from ...external.db.base import TaskDefinitionRepository, TaskInstanceRepository
from ...external.db.impl import create_task_instance_repo, create_task_definition_repo
from ...external.db.session import get_db_session, dialect, create_tables
from ...services.lifecycle_service import LifecycleService
from ...services.signal_service import SignalService
from ...services.observer_service import ObserverService
from ...drivers.schedulers.dispatcher import TaskDispatcher
from ...drivers.schedulers.cron_generator import cron_scheduler
from ...drivers.schedulers.health_checker import health_checker


def get_cache() -> RedisCacheClient:
    """
    返回 Redis 缓存客户端实例（无状态，可安全复用）。
    如果未来需要异步初始化，可改为 async def + startup event。
    """
    return RedisCacheClient()


def get_broker() -> RabbitMQDelayedMessageBroker:
    """
    返回 RabbitMQ 延迟消息代理（同时用作 MessageBroker 和 EventPublisher）。
    """
    return RabbitMQDelayedMessageBroker(settings.rabbitmq_url)


# ==============================
# 3. Repository 依赖（动态选择实现）
# ==============================

def get_task_definition_repo(
    session: AsyncSession = Depends(get_db_session),
) -> TaskDefinitionRepository:
    return create_task_definition_repo(session, dialect)


def get_task_instance_repo(
    session: AsyncSession = Depends(get_db_session),
) -> TaskInstanceRepository:
    return create_task_instance_repo(session, dialect)


# ==============================
# 4. Service 依赖（无状态，按需创建）
# ==============================

def get_lifecycle_service(
    broker: RabbitMQDelayedMessageBroker = Depends(get_broker),
    cache: RedisCacheClient = Depends(get_cache),
) -> LifecycleService:
    return LifecycleService(
        broker=broker,
        cache=cache,
    )


def get_signal_service(
    cache: RedisCacheClient = Depends(get_cache),
) -> SignalService:
    return SignalService(cache=cache)


def get_observer_service(
    event_publisher: RabbitMQDelayedMessageBroker = Depends(get_broker),
) -> ObserverService:
    return ObserverService(
        event_publisher=event_publisher,
        # webhook_registry 可在此处注入，如果需要
    )


def get_task_dispatcher(
    broker: RabbitMQDelayedMessageBroker = Depends(get_broker),
    lifecycle_service: LifecycleService = Depends(get_lifecycle_service),
) -> TaskDispatcher:
    """
    返回任务分发器实例
    """
    return TaskDispatcher(
        broker=broker,
        lifecycle_service=lifecycle_service,
        worker_url=settings.worker_callback_url
    )