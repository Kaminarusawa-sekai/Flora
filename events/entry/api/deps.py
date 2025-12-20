from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends
from ...config.settings import settings
from ...external.cache.redis_impl import RedisCacheClient

from ...external.db.base import EventDefinitionRepository, EventInstanceRepository
from ...external.db.impl import create_event_instance_repo, create_event_definition_repo
from ...external.db.session import get_db_session, dialect
from ...services.lifecycle_service import LifecycleService
from ...services.signal_service import SignalService
from ...services.observer_service import ObserverService


def get_cache() -> RedisCacheClient:
    """
    返回 Redis 缓存客户端实例（无状态，可安全复用）。
    如果未来需要异步初始化，可改为 async def + startup event。
    """
    return RedisCacheClient()



# ==============================
# 3. Repository 依赖（动态选择实现）
# ==============================

def get_event_definition_repo(
    session: AsyncSession = Depends(get_db_session),
) -> EventDefinitionRepository:
    return create_event_definition_repo(session, dialect)


def get_event_instance_repo(
    session: AsyncSession = Depends(get_db_session),
) -> EventInstanceRepository:
    return create_event_instance_repo(session, dialect)


# ==============================
# 4. Service 依赖（无状态，按需创建）
# ==============================

def get_lifecycle_service(
    
    cache: RedisCacheClient = Depends(get_cache),
) -> LifecycleService:
    return LifecycleService(
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

