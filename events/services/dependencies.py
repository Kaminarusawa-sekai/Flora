from external.cache.redis_impl import redis_client
from external.events.bus_impl_redis import RedisEventBus
from external.events.bus_impl_memory import MemoryEventBus
from external.client.agent_client import AgentClient
from external.db.base import AgentTaskHistoryRepository, AgentDailyMetricRepository
from external.db.impl import create_agent_task_history_repo, create_agent_daily_metric_repo
from external.db.session import async_session, dialect
from .lifecycle_service import LifecycleService
from .signal_service import SignalService
from .agent_monitor_service import AgentMonitorService


def get_redis_event_bus():
    """
    获取 Redis 事件总线实例
    :return: RedisEventBus 实例
    """
    return RedisEventBus(redis_client)


def get_memory_event_bus():
    """
    获取内存事件总线实例（用于测试）
    :return: MemoryEventBus 实例
    """
    return MemoryEventBus()


def get_lifecycle_service(event_bus=None):
    """
    获取生命周期服务实例
    :param event_bus: 事件总线实例，默认为 RedisEventBus
    :return: LifecycleService 实例
    """
    if event_bus is None:
        event_bus = get_redis_event_bus()
    return LifecycleService(
        event_bus=event_bus,
        cache=redis_client
    )


def get_signal_service():
    """
    获取信号服务实例
    :return: SignalService 实例
    """
    return SignalService(cache=redis_client)


async def get_agent_monitor_service(event_bus=None):
    """
    获取 Agent 监控服务实例
    :param event_bus: 事件总线实例，默认为 RedisEventBus
    :return: AgentMonitorService 实例
    """
    if event_bus is None:
        event_bus = get_redis_event_bus()
    # 创建 AgentClient 实例，使用默认 base_url
    agent_client = AgentClient()
    
    # 创建异步会话
    async with AsyncSessionFactory() as session:
        # 创建数据库仓库
        task_history_repo = create_agent_task_history_repo(session, dialect)
        daily_metric_repo = create_agent_daily_metric_repo(session, dialect)
        
        # 创建并返回服务实例
        return AgentMonitorService(
            cache=redis_client, 
            event_bus=event_bus, 
            task_history_repo=task_history_repo,
            daily_metric_repo=daily_metric_repo,
            agent_client=agent_client
        )
