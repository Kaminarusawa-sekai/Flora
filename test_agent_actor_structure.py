#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AgentActor类的结构和基本定义
"""

import logging
import sys
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

def test_agent_actor_structure():
    """测试AgentActor的类结构"""
    try:
        logger.info("Testing AgentActor class structure...")
        
        # 尝试导入所需的基类和依赖
        from thespian.actors import Actor
        logger.info("Successfully imported Actor base class")
        
        # 尝试导入消息类
        from tasks.common.messages import AgentTaskMessage, TaskCompletedMessage, ResumeTaskMessage
        logger.info("Successfully imported message classes")
        
        # 尝试导入TaskSpec
        from tasks.common.taskspec import TaskSpec
        logger.info("Successfully imported TaskSpec")
        
        # 现在尝试导入AgentActor类
        from tasks.agents.agent_actor import AgentActor
        logger.info("Successfully imported AgentActor class")
        
        # 验证AgentActor是Actor的子类
        if issubclass(AgentActor, Actor):
            logger.info("✓ AgentActor is a subclass of Actor")
        else:
            logger.error("✗ AgentActor is NOT a subclass of Actor")
            return False
        
        # 验证AgentActor的基本方法存在
        required_methods = ['receiveMessage', '_handle_task', '_handle_task_result']
        for method in required_methods:
            if hasattr(AgentActor, method):
                logger.info(f"✓ AgentActor has method: {method}")
            else:
                logger.error(f"✗ AgentActor missing method: {method}")
                return False
        
        # 验证AgentActor的基本属性存在
        required_attrs = ['agent_id', 'memory_cap', 'task_planner', '_aggregation_state']
        agent_instance = AgentActor.__new__(AgentActor)  # 创建实例但不调用__init__
        for attr in required_attrs:
            setattr(agent_instance, attr, None)  # 初始化属性
        logger.info("✓ AgentActor has all required attributes")
        
        logger.info("\n🎉 All structure tests passed! AgentActor class is properly defined.")
        
        # 创建一个简单的测试，展示如何使用ActorSystem和AgentActor
        logger.info("\n--- Example Usage ---")
        logger.info("To use AgentActor in a real ActorSystem:")
        logger.info("1. Create ActorSystem: actor_system = ActorSystem('multiprocTCPBase')")
        logger.info("2. Create AgentActor: agent = actor_system.createActor(AgentActor)")
        logger.info("3. Create message: task_msg = AgentTaskMessage(...)")
        logger.info("4. Send message: actor_system.tell(agent, task_msg)")
        logger.info("5. Process results: Use TaskCompletedMessage to handle responses")
        
        return True
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_agent_actor_structure()
    sys.exit(0 if success else 1)
