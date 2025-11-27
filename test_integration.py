"""
整合测试脚本
测试完整的任务流程，包括任务创建、规划、分发、执行和结果聚合
"""

import time
import logging
import sys
from thespian.actors import ActorSystem, ActorExitRequest
from agents.agent_actor import AgentActor
from init_plugins import init_plugins

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_integration.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def test_full_task_flow():
    """测试完整的任务流程"""
    logger.info("=== 开始整合测试 ===")
    print("=== 开始整合测试 ===")
    
    try:
        # 1. 初始化插件
        logger.info("1. 初始化插件...")
        print("\n1. 初始化插件...")
        init_plugins()
        logger.info("插件初始化完成")
        
        # 2. 创建Actor系统
        logger.info("2. 创建Actor系统...")
        print("\n2. 创建Actor系统...")
        asys = ActorSystem("multiprocTCPBase")
        logger.info("Actor系统创建完成")
        
        # 3. 创建AgentActor
        logger.info("3. 创建AgentActor...")
        print("3. 创建AgentActor...")
        agent_addr = asys.createActor(AgentActor, globalName="agent_actor")
        logger.info(f"AgentActor创建完成，地址: {agent_addr}")
        
        # 4. 初始化AgentActor
        logger.info("4. 初始化AgentActor...")
        print("4. 初始化AgentActor...")
        init_msg = {
            "message_type": "init",
            "agent_id": "test_agent_001"
        }
        asys.tell(agent_addr, init_msg)
        logger.info("初始化消息发送完成")
        
        # 等待初始化完成
        time.sleep(2)
        
        # 5. 发送测试任务
        logger.info("5. 发送测试任务...")
        print("\n5. 发送测试任务...")
        test_task = {
            "message_type": "agent_task",
            "task_id": "test_task_001",
            "description": "分析最近的销售数据",
            "user_id": "test_user_001"
        }
        asys.tell(agent_addr, test_task)
        logger.info(f"测试任务发送完成，任务ID: {test_task['task_id']}")
        
        # 6. 等待任务执行
        logger.info("6. 等待任务执行...")
        print("\n6. 等待任务执行...")
        time.sleep(10)
        
        # 7. 发送循环任务测试
        logger.info("7. 发送循环任务测试...")
        print("\n7. 发送循环任务测试...")
        loop_task = {
            "message_type": "agent_task",
            "task_id": "loop_task_001",
            "description": "每天生成销售日报",
            "user_id": "test_user_001"
        }
        asys.tell(agent_addr, loop_task)
        logger.info(f"循环任务发送完成，任务ID: {loop_task['task_id']}")
        
        # 等待循环任务注册
        time.sleep(5)
        
        # 8. 触发循环任务
        logger.info("8. 触发循环任务...")
        print("\n8. 触发循环任务...")
        from capability_actors.loop_scheduler_actor import LoopSchedulerActor
        scheduler_addr = asys.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        trigger_msg = {
            "type": "trigger_task_now",
            "task_id": "loop_task_001"
        }
        asys.tell(scheduler_addr, trigger_msg)
        logger.info(f"循环任务触发完成，任务ID: {trigger_msg['task_id']}")
        
        # 等待循环任务执行
        time.sleep(10)
        
        # 9. 关闭Actor系统
        logger.info("9. 关闭Actor系统...")
        print("\n9. 关闭Actor系统...")
        asys.shutdown()
        logger.info("Actor系统关闭完成")
        
        logger.info("=== 整合测试完成 ===")
        print("\n=== 整合测试完成 ===")
        return True
    except Exception as e:
        logger.error(f"测试过程中发生错误: {e}", exc_info=True)
        print(f"\n测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_full_task_flow()
    sys.exit(0 if success else 1)
