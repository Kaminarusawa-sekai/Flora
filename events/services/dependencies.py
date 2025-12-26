from external.cache.redis_impl import redis_client
from external.events.bus_impl_redis import RedisEventBus
from external.events.bus_impl_memory import MemoryEventBus
from external.client.agent_client import AgentClient
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


def get_agent_monitor_service():
    """
    获取 Agent 监控服务实例
    :return: AgentMonitorService 实例
    """
    # 创建 AgentClient 实例，使用默认 base_url
    agent_client = AgentClient()
    return AgentMonitorService(cache=redis_client, agent_client=agent_client)
