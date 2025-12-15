from fastapi import Depends
from ...external.cache.redis_impl import RedisCacheClient
from ...external.messaging.rabbitmq_delayed import RabbitMQDelayedMessageBroker
from ...external.db.sqlalchemy_impl import SQLAlchemyTaskDefinitionRepo, SQLAlchemyTaskInstanceRepo
from ...services.lifecycle_service import LifecycleService
from ...services.signal_service import SignalService
from ...services.observer_service import ObserverService
from ...config.settings import settings
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# 创建数据库引擎和会话工厂
engine = create_async_engine(settings.db_url)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# 单例服务实例
_lifecycle_svc: LifecycleService = None
_signal_svc: SignalService = None
_observer_svc: ObserverService = None


async def get_db_session() -> AsyncSession:
    """获取数据库会话"""
    async with async_session() as session:
        yield session


def init_services():
    """初始化所有服务"""
    global _lifecycle_svc, _signal_svc, _observer_svc
    
    # 初始化 L2 组件
    cache = RedisCacheClient()
    broker = RabbitMQDelayedMessageBroker(settings.rabbitmq_url)
    
    # 创建数据库会话
    async def get_session():
        return async_session()
    
    # 初始化存储库
    session = async_session()
    def_repo = SQLAlchemyTaskDefinitionRepo(session)
    inst_repo = SQLAlchemyTaskInstanceRepo(session)
    
    # 初始化事件发布器（复用消息队列）
    event_publisher = broker
    
    # 初始化 L3 服务
    _lifecycle_svc = LifecycleService(
        def_repo=def_repo,
        inst_repo=inst_repo,
        broker=broker,
        cache=cache
    )
    
    _signal_svc = SignalService(
        cache=cache,
        inst_repo=inst_repo
    )
    
    _observer_svc = ObserverService(
        inst_repo=inst_repo,
        event_publisher=event_publisher
    )


def get_lifecycle_service() -> LifecycleService:
    """获取生命周期服务"""
    return _lifecycle_svc


def get_signal_service() -> SignalService:
    """获取信号服务"""
    return _signal_svc


def get_observer_service() -> ObserverService:
    """获取观察者服务"""
    return _observer_svc
