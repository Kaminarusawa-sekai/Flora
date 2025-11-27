"""
全局组件初始化
负责初始化和启动系统的所有核心组件
"""
import logging
from thespian.actors import ActorSystem
from threading import Thread

# 导入配置
from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

# 导入注册表
from agents.agent_registry import AgentRegistry

# 导入桥接器
from rabbit_bridge import start_rabbit_bridge

# 导入插件初始化
from init_plugins import init_plugins

# 导入事件总线
from events.event_bus import event_bus

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 全局变量
_actor_system = None
_registry = None
_rabbit_thread = None


async def init_global_components():
    """
    初始化全局组件
    包括：
    1. 插件系统
    2. Thespian Actor System
    3. Agent注册表
    4. RabbitMQ桥接器
    5. 事件总线
    """
    global _actor_system, _registry, _rabbit_thread

    try:
        # 1. 初始化插件系统
        logger.info("Initializing plugin system...")
        init_plugins()
        logger.info("✓ Plugin system initialized")

        # 2. 初始化Thespian Actor System
        logger.info("Initializing Thespian Actor System...")
        _actor_system = ActorSystem("multiprocTCPBase")
        logger.info("✓ Thespian Actor System initialized")

        # 3. 初始化Agent注册表
        logger.info("Initializing Agent Registry...")
        _registry = AgentRegistry.get_instance(
            uri=NEO4J_URI,
            user=NEO4J_USER,
            password=NEO4J_PASSWORD
        )
        logger.info("✓ Agent Registry initialized")

        # 4. 初始化RabbitMQ桥接器（在后台线程中运行）
        logger.info("Initializing RabbitMQ bridge...")
        def start_bridge():
            try:
                start_rabbit_bridge()
            except Exception as e:
                logger.error(f"RabbitMQ bridge error: {e}")

        _rabbit_thread = Thread(target=start_bridge, daemon=True)
        _rabbit_thread.start()
        logger.info("✓ RabbitMQ bridge initialized")

        # 5. 初始化事件总线
        logger.info("Initializing Event Bus...")
        # 事件总线已经是单例，这里只是确认初始化
        logger.info(f"✓ Event Bus initialized with {event_bus.get_subscribers_count()} subscribers")

        # 6. 创建全局LoopSchedulerActor
        logger.info("Creating global LoopSchedulerActor...")
        from capability_actors.loop_scheduler_actor import LoopSchedulerActor
        loop_scheduler = _actor_system.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        logger.info("✓ Global LoopSchedulerActor created")

        logger.info("=" * 60)
        logger.info("All global components initialized successfully!")
        logger.info("=" * 60)

        return {
            "actor_system": _actor_system,
            "registry": _registry,
            "rabbit_thread": _rabbit_thread,
            "event_bus": event_bus
        }

    except Exception as e:
        logger.error(f"Failed to initialize global components: {e}", exc_info=True)
        raise


def get_actor_system():
    """获取全局Actor System"""
    global _actor_system
    if _actor_system is None:
        raise RuntimeError("Actor System not initialized. Call init_global_components() first.")
    return _actor_system


def get_registry():
    """获取全局Agent注册表"""
    global _registry
    if _registry is None:
        raise RuntimeError("Agent Registry not initialized. Call init_global_components() first.")
    return _registry


def get_event_bus():
    """获取全局事件总线"""
    return event_bus


def shutdown_global_components():
    """
    关闭全局组件
    """
    global _actor_system, _registry, _rabbit_thread

    logger.info("Shutting down global components...")

    # 1. 关闭Actor System
    if _actor_system:
        logger.info("Shutting down Actor System...")
        _actor_system.shutdown()
        _actor_system = None
        logger.info("✓ Actor System shut down")

    # 2. 关闭Agent注册表
    if _registry:
        logger.info("Closing Agent Registry...")
        _registry.close()
        _registry = None
        logger.info("✓ Agent Registry closed")

    # 3. RabbitMQ桥接器会随主线程自动结束（daemon=True）
    if _rabbit_thread:
        logger.info("✓ RabbitMQ bridge thread will terminate")
        _rabbit_thread = None

    # 4. 清空事件总线
    logger.info("Clearing Event Bus...")
    event_bus.clear()
    logger.info("✓ Event Bus cleared")

    logger.info("All global components shut down successfully!")


if __name__ == "__main__":
    # 测试初始化
    import sys
    import asyncio

    try:
        # 初始化全局组件
        components = asyncio.run(init_global_components())
        logger.info("Test initialization successful!")

        # 等待用户输入以保持程序运行
        input("Press Enter to shutdown...")

    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 关闭全局组件
        shutdown_global_components()
        logger.info("Test completed!")

