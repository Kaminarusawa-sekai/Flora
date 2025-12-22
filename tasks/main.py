#!/usr/bin/env python3
"""
Flora 多智能体协作系统 - 主启动文件

用于启动 FastAPI 服务的入口点，同时支持 RabbitMQ 消息监听。
注意：本脚本应通过 `python tasks/main.py` 启动，不支持 uvicorn 直接加载。
"""

import logging
import argparse
import atexit
from uvicorn import run
from entry_layer.api_server import create_api_server

# 导入消息队列和 ActorSystem 相关模块
try:
    from external.message_queue import MessageQueueFactory
    from thespian.actors import ActorSystem
    from agents.agent_actor import AgentActor
    RABBITMQ_AVAILABLE = True
except ImportError as e:
    # 先初始化 logger 再记录（避免 NameError）
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to import message queue dependencies: {e}")
    RABBITMQ_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量，用于在退出时清理资源
_global_rabbitmq_listener = None
_global_actor_system = None


def start_rabbitmq_listener(rabbitmq_url='localhost'):
    """
    启动消息队列监听器
    
    Args:
        rabbitmq_url: RabbitMQ服务器URL
    
    Returns:
        MessageQueueListener: 消息队列监听器实例，或 None
    """
    global _global_actor_system, _global_rabbitmq_listener

    if not RABBITMQ_AVAILABLE:
        logger.warning("RabbitMQ 依赖未安装，跳过消息队列监听")
        return None

    try:
        # 初始化 Actor 系统（使用 TCP 多进程模式）
        actor_system = ActorSystem('multiprocTCPBase')
        _global_actor_system = actor_system  # 保存引用以便清理

        # 创建 AgentActor
        agent_actor_ref = actor_system.createActor(AgentActor)

        # 使用工厂创建监听器
        listener = MessageQueueFactory.create_listener(
            queue_type='rabbitmq',
            actor_system=actor_system,
            agent_actor_ref=agent_actor_ref,
            config={'rabbitmq_url': rabbitmq_url}
        )

        if listener:
            listener.start_in_thread()
            _global_rabbitmq_listener = listener
            logger.info("RabbitMQ listener started successfully.")
            return listener
        else:
            logger.error("Failed to create RabbitMQ listener.")
            return None

    except Exception as e:
        logger.exception(f"Failed to start RabbitMQ listener: {e}")
        return None


def cleanup_resources():
    """程序退出时清理资源"""
    global _global_rabbitmq_listener, _global_actor_system

    if _global_rabbitmq_listener:
        try:
            logger.info("Stopping RabbitMQ listener...")
            _global_rabbitmq_listener.stop()
        except Exception as e:
            logger.error(f"Error stopping RabbitMQ listener: {e}")

    if _global_actor_system:
        try:
            logger.info("Shutting down ActorSystem...")
            _global_actor_system.shutdown()
        except Exception as e:
            logger.error(f"Error shutting down ActorSystem: {e}")


def main():
    """
    主函数：启动 FastAPI 服务和 RabbitMQ 监听器（如启用）
    """
    parser = argparse.ArgumentParser(description='Flora API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode in FastAPI (detailed errors, etc.)')
    parser.add_argument('--rabbitmq', action='store_true', help='Enable RabbitMQ task listener')
    parser.add_argument('--rabbitmq-url', default='localhost', help='RabbitMQ server URL')

    args = parser.parse_args()

    # 注册退出清理函数
    atexit.register(cleanup_resources)

    # 启动 RabbitMQ 监听器（如果启用）
    if args.rabbitmq:
        start_rabbitmq_listener(args.rabbitmq_url)

    try:
        # 创建 FastAPI 应用（debug 模式仅影响 API 行为，不影响 reload）
        app = create_api_server(config={"debug": args.debug})

        logger.info(f"Starting Flora API Server on http://{args.host}:{args.port} (debug={args.debug})")
        logger.info("Press Ctrl+C to stop.")

        # 启动 Uvicorn —— 关键：reload=False（始终禁用热重载）
        run(
            app,
            host=args.host,
            port=args.port,
            reload=False,  # ←←← 强制禁用热重载
            log_level="info"
        )

    except KeyboardInterrupt:
        logger.info("Received KeyboardInterrupt. Shutting down...")
    except Exception as e:
        logger.exception(f"Unexpected error during startup: {e}")
    finally:
        cleanup_resources()


if __name__ == '__main__':
    main()