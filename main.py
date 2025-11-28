"""系统启动主入口"""
import logging
import argparse
import threading
from typing import Dict, Any, Optional

# 初始化日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 导入能力模块
from capabilities import init_capabilities
from capabilities.llm.interface import ILLMCapability
from capabilities.llm_memory.interface import IMemoryCapability
from capabilities.text_to_sql.text_to_sql import ITextToSQL

# 导入API服务器
from entry_layer.api_server import APIServer

# 导入Thespian Actor系统相关组件
from thespian.actors import ActorSystem
from agents.agent_actor import AgentActor
from capability_actors.loop_scheduler_actor import LoopSchedulerActor


def init_actor_system() -> ActorSystem:
    """
    初始化Thespian Actor系统
    
    Returns:
        ActorSystem: Thespian Actor系统实例
    """
    logger.info("=== 初始化Thespian Actor系统 ===")
    
    # 初始化Actor系统
    actor_system = ActorSystem('simpleSystemBase')
    
    # 启动核心Actor
    logger.info("启动核心Actor...")
    
    # 启动AgentActor
    agent_actor = actor_system.createActor(AgentActor)
    logger.info(f"✓ 成功启动AgentActor: {agent_actor}")
    
    # 启动LoopSchedulerActor
    loop_scheduler_actor = actor_system.createActor(LoopSchedulerActor)
    logger.info(f"✓ 成功启动LoopSchedulerActor: {loop_scheduler_actor}")
    
    return actor_system


def start_api_server(config: Optional[Dict[str, Any]] = None) -> APIServer:
    """
    启动FastAPI服务器
    
    Args:
        config: 服务器配置
        
    Returns:
        APIServer: API服务器实例
    """
    logger.info("=== 启动FastAPI服务器 ===")
    
    # 创建API服务器实例
    api_server = APIServer(config)
    
    # 在后台线程中启动服务器
    host = config.get('host', '0.0.0.0') if config else '0.0.0.0'
    port = config.get('port', 8000) if config else 8000
    
    server_thread = threading.Thread(
        target=api_server.run,
        kwargs={'host': host, 'port': port},
        daemon=True
    )
    server_thread.start()
    
    logger.info(f"✓ FastAPI服务器已启动，监听地址: http://{host}:{port}")
    logger.info(f"✓ API文档地址: http://{host}:{port}/docs")
    logger.info(f"✓ 健康检查地址: http://{host}:{port}/health")
    
    return api_server


def run_system_demo():
    """
    运行系统演示（原有功能）
    """
    print("=== 初始化能力模块 ===")
    
    # 初始化所有能力
    manager = init_capabilities()
    
    print("\n=== 获取LLM能力 ===")
    try:
        # 获取LLM能力
        llm = manager.get_capability("qwen", expected_type=ILLMCapability)
        print(f"✓ 成功获取LLM能力: {type(llm).__name__}")
        print(f"✓ 能力类型: {llm.get_capability_type()}")
    except Exception as e:
        print(f"✗ 获取LLM能力失败: {e}")
    
    print("\n=== 获取Memory能力 ===")
    try:
        # 获取Memory能力
        memory = manager.get_capability("core_memory", expected_type=IMemoryCapability)
        print(f"✓ 成功获取Memory能力: {type(memory).__name__}")
        print(f"✓ 能力类型: {memory.get_capability_type()}")
    except Exception as e:
        print(f"✗ 获取Memory能力失败: {e}")
    
    print("\n=== 获取TextToSQL能力 ===")
    try:
        # 获取TextToSQL能力
        text_to_sql = manager.get_capability("vanna", expected_type=ITextToSQL)
        print(f"✓ 成功获取TextToSQL能力: {type(text_to_sql).__name__}")
        print(f"✓ 能力类型: {text_to_sql.get_capability_type()}")
    except Exception as e:
        print(f"✗ 获取TextToSQL能力失败: {e}")
    
    print("\n=== 示例完成 ===")
    print("\n使用说明:")
    print("1. 修改config.json文件可以配置各能力的参数")
    print("2. 调用manager.update_capability_config()可以动态更新配置")
    print("3. 调用manager.save_config()可以保存配置到文件")
    print("4. 所有能力都实现了统一的生命周期管理接口")


def main():
    """
    主函数，启动整个系统
    """
    parser = argparse.ArgumentParser(description='Flora 多智能体协作系统')
    parser.add_argument('--demo', action='store_true', help='运行系统演示模式')
    parser.add_argument('--host', default='0.0.0.0', help='API服务器主机地址')
    parser.add_argument('--port', type=int, default=8000, help='API服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    
    args = parser.parse_args()
    
    if args.demo:
        # 运行演示模式
        run_system_demo()
        return
    
    logger.info("=== Flora 多智能体协作系统启动 ===")
    
    # 1. 初始化能力模块
    logger.info("=== 初始化能力模块 ===")
    manager = init_capabilities()
    logger.info("✓ 能力模块初始化完成")
    
    # 2. 初始化Actor系统
    actor_system = init_actor_system()
    
    # 3. 启动API服务器
    api_config = {
        'debug': args.debug,
        'host': args.host,
        'port': args.port
    }
    api_server = start_api_server(api_config)
    
    logger.info("\n=== 系统启动完成 ===")
    logger.info("Flora 多智能体协作系统已成功启动！")
    logger.info("按 Ctrl+C 停止系统...")
    
    try:
        # 保持主进程运行
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("\n=== 正在停止系统 ===")
        
        # 关闭Actor系统
        logger.info("关闭Thespian Actor系统...")
        actor_system.shutdown()
        logger.info("✓ Actor系统已关闭")
        
        logger.info("系统已成功停止！")


if __name__ == "__main__":
    main()