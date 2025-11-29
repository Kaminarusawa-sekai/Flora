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


# def init_actor_system() -> ActorSystem:
#     """
#     初始化Thespian Actor系统
    
#     Returns:
#         ActorSystem: Thespian Actor系统实例
#     """
#     logger.info("=== 初始化Thespian Actor系统 ===")
    
#     # 初始化Actor系统
#     actor_system = ActorSystem('simpleSystemBase')
    
#     # 启动核心Actor
#     logger.info("启动核心Actor...")
    
#     # 启动AgentActor
#     agent_actor = actor_system.createActor(AgentActor)
#     logger.info(f"✓ 成功启动AgentActor: {agent_actor}")
    
#     # 启动LoopSchedulerActor
#     loop_scheduler_actor = actor_system.createActor(LoopSchedulerActor)
#     logger.info(f"✓ 成功启动LoopSchedulerActor: {loop_scheduler_actor}")
    
#     return actor_system


# def start_api_server(config: Optional[Dict[str, Any]] = None) -> APIServer:
#     """
#     启动FastAPI服务器
    
#     Args:
#         config: 服务器配置
        
#     Returns:
#         APIServer: API服务器实例
#     """
#     logger.info("=== 启动FastAPI服务器 ===")
    
#     # 创建API服务器实例
#     api_server = APIServer(config)
    
#     # 在后台线程中启动服务器
#     host = config.get('host', '0.0.0.0') if config else '0.0.0.0'
#     port = config.get('port', 8000) if config else 8000
    
#     server_thread = threading.Thread(
#         target=api_server.run,
#         kwargs={'host': host, 'port': port},
#         daemon=True
#     )
#     server_thread.start()
    
#     logger.info(f"✓ FastAPI服务器已启动，监听地址: http://{host}:{port}")
#     logger.info(f"✓ API文档地址: http://{host}:{port}/docs")
#     logger.info(f"✓ 健康检查地址: http://{host}:{port}/health")
    
#     return api_server


# def run_system_demo():
#     """
#     运行系统演示（原有功能）
#     """
#     print("=== 初始化能力模块 ===")
    
#     # 初始化所有能力
#     manager = init_capabilities()
    
#     print("\n=== 获取LLM能力 ===")
#     try:
#         # 获取LLM能力
#         llm = manager.get_capability("qwen", expected_type=ILLMCapability)
#         print(f"✓ 成功获取LLM能力: {type(llm).__name__}")
#         print(f"✓ 能力类型: {llm.get_capability_type()}")
#     except Exception as e:
#         print(f"✗ 获取LLM能力失败: {e}")
    
#     print("\n=== 获取Memory能力 ===")
#     try:
#         # 获取Memory能力
#         memory = manager.get_capability("core_memory", expected_type=IMemoryCapability)
#         print(f"✓ 成功获取Memory能力: {type(memory).__name__}")
#         print(f"✓ 能力类型: {memory.get_capability_type()}")
#     except Exception as e:
#         print(f"✗ 获取Memory能力失败: {e}")
    
#     print("\n=== 获取TextToSQL能力 ===")
#     try:
#         # 获取TextToSQL能力
#         text_to_sql = manager.get_capability("vanna", expected_type=ITextToSQL)
#         print(f"✓ 成功获取TextToSQL能力: {type(text_to_sql).__name__}")
#         print(f"✓ 能力类型: {text_to_sql.get_capability_type()}")
#     except Exception as e:
#         print(f"✗ 获取TextToSQL能力失败: {e}")
    
#     print("\n=== 示例完成 ===")
#     print("\n使用说明:")
#     print("1. 修改config.json文件可以配置各能力的参数")
#     print("2. 调用manager.update_capability_config()可以动态更新配置")
#     print("3. 调用manager.save_config()可以保存配置到文件")
#     print("4. 所有能力都实现了统一的生命周期管理接口")


# def main():
#     """
#     主函数，启动整个系统
#     """
#     parser = argparse.ArgumentParser(description='Flora 多智能体协作系统')
#     parser.add_argument('--demo', action='store_true', help='运行系统演示模式')
#     parser.add_argument('--host', default='0.0.0.0', help='API服务器主机地址')
#     parser.add_argument('--port', type=int, default=8000, help='API服务器端口')
#     parser.add_argument('--debug', action='store_true', help='调试模式')




    
#     args = parser.parse_args()
    
#     if args.demo:
#         # 运行演示模式
#         run_system_demo()
#         return
    
#     logger.info("=== Flora 多智能体协作系统启动 ===")
    
#     # 1. 初始化能力模块
#     logger.info("=== 初始化能力模块 ===")
#     manager = init_capabilities()
#     logger.info("✓ 能力模块初始化完成")
    
#     # 2. 初始化Actor系统
#     actor_system = init_actor_system()
    
#     # 3. 启动API服务器
#     api_config = {
#         'debug': args.debug,
#         'host': args.host,
#         'port': args.port
#     }
#     api_server = start_api_server(api_config)
    
#     logger.info("\n=== 系统启动完成 ===")
#     logger.info("Flora 多智能体协作系统已成功启动！")
#     logger.info("按 Ctrl+C 停止系统...")
    
#     try:
#         # 保持主进程运行
#         while True:
#             pass
#     except KeyboardInterrupt:
#         logger.info("\n=== 正在停止系统 ===")
        
#         # 关闭Actor系统
#         logger.info("关闭Thespian Actor系统...")
#         actor_system.shutdown()
#         logger.info("✓ Actor系统已关闭")
        
#         logger.info("系统已成功停止！")


# if __name__ == "__main__":
#     main()
"""系统启动主入口

完整的Actor系统架构：
1. RouterActor：全局唯一路由，管理AgentActor实例的唯一性
2. InteractionActor：前台对话处理
3. AgentActor：后台任务执行
4. ExecutionActor：具体任务执行

消息流：
用户输入 → RouterActor → InteractionActor → AgentActor → ExecutionActor
          ↑                    ↓                    ↓
          └────────────────────┴────────────────────┘
                        (结果返回)
"""

import logging
import argparse
import threading
import time
from typing import Dict, Any, Optional

# Thespian
from thespian.actors import ActorSystem, ActorAddress

# 引入Actor
from agents.router_actor import RouterActor
from agents.interaction_actor import InteractionActor
from agents.agent_actor import AgentActor
from capability_actors.loop_scheduler_actor import LoopSchedulerActor

# 引入能力初始化
from capabilities import init_capabilities
from capabilities.llm.interface import ILLMCapability
from rabbit_bridge import start_rabbit_bridge


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --------------------------------

class SystemContext:
    """用于在main函数中传递系统组件的上下文容器"""
    def __init__(self):
        self.actor_system = None
        self.router_actor = None
        self.interaction_actor = None
        self.agent_actor = None
        self.loop_scheduler_actor = None


def init_actor_system(context: SystemContext, system_base: str) -> ActorSystem:
    """
    初始化Thespian Actor系统并组装Actor关系
    """
    logger.info(f"=== 初始化 Thespian Actor 系统 ({system_base}) ===")

    # 1. 初始化系统基座
    # MODIFIED: 使用参数传入的 system_base
    system = ActorSystem(system_base)  
    context.actor_system = system

    logger.info("启动核心 Actors...")

    # 2. 启动 RouterActor（全局唯一路由）
    router_actor = system.createActor(RouterActor, globalName="global_router")
    context.router_actor = router_actor
    logger.info(f"✓ RouterActor 已启动: {router_actor}")

    # 3. 启动 后台执行 AgentActor
    agent_actor = system.createActor(AgentActor)
    context.agent_actor = agent_actor

    # 初始化AgentActor
    init_msg = {
        "message_type": "init",
        "agent_id": "default_agent"
    }
    system.tell(agent_actor, init_msg)

    logger.info(f"✓ 后台 AgentActor 已启动: {agent_actor}")

    # 4. 启动 前台交互 InteractionActor
    interaction_actor = system.createActor(InteractionActor)
    context.interaction_actor = interaction_actor
    logger.info(f"✓ 前台 InteractionActor 已启动: {interaction_actor}")

    # 5. 组装：告诉前台，后台在哪里
    logger.info("正在组装 Actor 关系...")
    system.tell(interaction_actor, {
        "message_type": "configure",
        "backend_addr": agent_actor
    })
    logger.info("✓ InteractionActor 已配置 backend_addr")

    # 6. 启动 LoopSchedulerActor（循环任务调度）
    # IMPORTANT: globalName="loop_scheduler" 是 Bridge 找到它的关键
    loop_scheduler_actor = system.createActor(LoopSchedulerActor, globalName="loop_scheduler")
    context.loop_scheduler_actor = loop_scheduler_actor
    logger.info(f"✓ LoopSchedulerActor 已启动: {loop_scheduler_actor}")

    return system


def send_test_message(system: ActorSystem, target_actor: ActorAddress):
    # ... (保持原样) ...
    logger.info("\n=== 发送测试消息 ===")
    time.sleep(2)  
    test_msg = {
        "message_type": "user_input",
        "user_id": "test_admin_001",
        "content": "帮我查询一下上个月的销售数据",
        "msg_id": "msg_test_1"
    }
    logger.info(f"发送模拟用户消息: {test_msg['content']}")
    try:
        response = system.ask(target_actor, test_msg, timeout=30)
        logger.info(f"收到系统回复: {response}")
    except Exception as e:
        logger.error(f"测试消息超时或出错: {e}")
    logger.info("=== 测试结束 ===\n")


def start_api_server(config: Optional[Dict[str, Any]] = None, actor_context: SystemContext = None):
    # ... (保持原样) ...
    logger.info("=== 启动 FastAPI 服务器 ===")
    host = config.get('host', '0.0.0.0') if config else '0.0.0.0'
    port = config.get('port', 8000) if config else 8000
    logger.info(f"✓ (模拟) FastAPI 服务器启动在: http://{host}:{port}")
    logger.info(f"提示: 实际部署时需要将InteractionActor地址注入到API Server")


def main():
    parser = argparse.ArgumentParser(description='Flora 多智能体协作系统')
    parser.add_argument('--test', action='store_true', help='启动后发送测试消息')
    parser.add_argument('--host', default='0.0.0.0', help='API服务器主机地址')
    parser.add_argument('--port', type=int, default=8000, help='API服务器端口')
    parser.add_argument('--debug', action='store_true', help='调试模式')
    # NEW: 添加 RabbitMQ 配置参数
    parser.add_argument('--mq-url', default='amqp://guest:guest@localhost:5672/', help='RabbitMQ 连接地址')
    args = parser.parse_args()

    logger.info("=== Flora 多智能体协作系统启动 ===")
    
    # MODIFIED: 推荐使用 multiprocTCPBase 以更好地支持 Bridge 和外部通信
    # simpleSystemBase 在多线程/阻塞操作下可能会有问题
    SYSTEM_BASE = 'simpleSystemBase' 
    
    # 1. 初始化能力模块
    logger.info("=== 初始化能力模块 ===")
    init_capabilities()
    logger.info("✓ 能力模块初始化完成\n")

    # 2. 初始化 Actor 系统
    sys_context = SystemContext()
    init_actor_system(sys_context, system_base=SYSTEM_BASE)

    logger.info("\n=== 系统启动完成 ===")
    # ... (日志保持原样) ...

    # === NEW: 启动 RabbitMQ Bridge (后台线程) ===
    logger.info("=== 启动外部事件桥接器 ===")
    mq_thread = threading.Thread(
        target=start_rabbit_bridge,
        kwargs={
            "thespian_system_name": SYSTEM_BASE,
        },
        daemon=True  # 设置为守护线程，主程序退出时它也会自动退出
    )
    mq_thread.start()
    logger.info("✓ RabbitMQ Bridge 线程已启动")
    # ==========================================

    # 3. (可选) 发送测试消息

    send_test_message(sys_context.actor_system, sys_context.interaction_actor)

    # 4. 启动 API 服务器
    api_config = {
        'host': args.host,
        'port': args.port,
        'debug': args.debug
    }
    start_api_server(api_config, actor_context=sys_context)

    logger.info("系统运行中... 按 Ctrl+C 停止")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n正在停止系统...")
        sys_context.actor_system.shutdown()
        logger.info("系统已停止")


if __name__ == "__main__":
    main()