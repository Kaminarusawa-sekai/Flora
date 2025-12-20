from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Depends
from ...config.settings import settings
from ...external.cache.redis_impl import RedisCacheClient
from ...external.events.bus_impl_memory import MemoryEventBus
from ...external.events.bus_impl_redis import RedisEventBus

from ...external.db.base import EventDefinitionRepository, EventInstanceRepository
from ...external.db.impl import create_event_instance_repo, create_event_definition_repo
from ...external.db.session import get_db_session, dialect
from ...services.lifecycle_service import LifecycleService
from ...services.signal_service import SignalService
from ...services.observer_service import ObserverService
from ...services.websocket_manager import ConnectionManager


def get_cache() -> RedisCacheClient:
    """
    返回 Redis 缓存客户端实例（无状态，可安全复用）。
    如果未来需要异步初始化，可改为 async def + startup event。
    """
    return RedisCacheClient()


def get_broker():
    """
    返回事件总线实例，根据配置选择使用内存实现或Redis实现
    """
    if settings.use_redis:
        return RedisEventBus(get_cache())
    else:
        return MemoryEventBus()


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
# 4. WebSocket 连接管理器（单例）
# ==============================

# 创建单例的ConnectionManager实例
connection_manager_instance = ConnectionManager()

def get_connection_manager() -> ConnectionManager:
    """
    返回WebSocket连接管理器实例（单例模式）
    """
    return connection_manager_instance


# ==============================
# 5. Service 依赖（无状态，按需创建）
# ==============================


def get_lifecycle_service(
    event_bus = Depends(get_broker),
    cache: RedisCacheClient = Depends(get_cache),
) -> LifecycleService:
    return LifecycleService(
        event_bus=event_bus,
        cache=cache,
    )



def get_signal_service(
    cache: RedisCacheClient = Depends(get_cache),
) -> SignalService:
    return SignalService(cache=cache)



def get_observer_service(
    event_bus = Depends(get_broker),
    connection_manager: ConnectionManager = Depends(get_connection_manager),
    cache: RedisCacheClient = Depends(get_cache),
) -> ObserverService:
    return ObserverService(
        event_bus=event_bus,
        connection_manager=connection_manager,
        cache=cache,
        # webhook_registry 可在此处注入，如果需要
    )

