#!/usr/bin/env python3
"""
Flora 多智能体协作系统 - 主启动文件

用于启动 FastAPI 服务的入口点，同时支持 RabbitMQ 消息监听
"""

import logging
import argparse
from uvicorn import run
from entry_layer.api_server import create_api_server

# 导入消息队列工厂和ActorSystem相关模块
try:
    from external.message_queue import MessageQueueFactory
    from thespian.actors import ActorSystem
    from agents.agent_actor import AgentActor
    RABBITMQ_AVAILABLE = True
except ImportError as e:
    logger = logging.getLogger(__name__)
    logger.warning(f"Failed to import dependencies: {e}")
    RABBITMQ_AVAILABLE = False

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_rabbitmq_listener(rabbitmq_url='localhost'):
    """
    启动消息队列监听器
    
    Args:
        rabbitmq_url: RabbitMQ服务器URL
    
    Returns:
        MessageQueueListener: 消息队列监听器实例
        None: 如果启动失败
    """
    if not RABBITMQ_AVAILABLE:
        logger.warning("依赖未安装，跳过消息队列监听")
        return None
    
    # 初始化 Actor 系统
    actor_system = ActorSystem('multiprocTCPBase')
    # 获取 AgentActor 的地址
    agent_actor_ref = actor_system.createActor(AgentActor)
    
    # 使用工厂模式创建监听器
    listener = MessageQueueFactory.create_listener(
        queue_type='rabbitmq',
        actor_system=actor_system,
        agent_actor_ref=agent_actor_ref,
        config={'rabbitmq_url': rabbitmq_url}
    )
    
    if listener:
        listener.start_in_thread()
    
    return listener

def main():
    """
    主函数，启动 FastAPI 服务和 RabbitMQ 监听
    """
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='Flora API Server')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Run in debug mode')
    parser.add_argument('--rabbitmq', action='store_true', help='Enable RabbitMQ listener')
    parser.add_argument('--rabbitmq-url', default='localhost', help='RabbitMQ server URL')
    
    args = parser.parse_args()
    
    # 启动消息队列监听器（如果启用）
    rabbitmq_listener = None
    if args.rabbitmq:
        rabbitmq_listener = start_rabbitmq_listener(args.rabbitmq_url)
    
    try:
        # 创建 FastAPI 应用实例
        app = create_api_server(config={"debug": args.debug})
        
        # 启动 Uvicorn 服务
        logger.info(f"Starting Flora API Server on {args.host}:{args.port}")
        run(
            app,
            host=args.host,
            port=args.port,
            reload=args.debug
        )
    finally:
        # 停止 RabbitMQ 监听器
        if rabbitmq_listener:
            rabbitmq_listener.stop()

if __name__ == '__main__':
    main()

