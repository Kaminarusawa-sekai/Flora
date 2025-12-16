#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试AgentActor类的消息处理功能
"""

import logging
import sys
from thespian.actors import ActorSystem
from tasks.agents.agent_actor import AgentActor
from tasks.common.messages import AgentTaskMessage

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

logger = logging.getLogger(__name__)

def test_agent_actor():
    """测试AgentActor的消息处理"""
    # 创建ActorSystem
    actor_system = ActorSystem('multiprocTCPBase')
    
    try:
        # 创建AgentActor实例
        agent_actor = actor_system.createActor(AgentActor)
        logger.info(f"Created AgentActor with address: {agent_actor}")
        
        # 构造AgentTaskMessage
        task_message = AgentTaskMessage(
            agent_id="test_agent",
            task_id="test_task_123",
            user_id="test_user",
            content="测试任务内容",
            description="测试AgentActor的消息处理",
            task_path="",
            trace_id="test_trace_456",
            global_context={},
            enriched_context={}
        )
        
        logger.info(f"Sending AgentTaskMessage: {task_message}")
        
        # 发送消息给AgentActor
        actor_system.tell(agent_actor, task_message)
        
        logger.info("Message sent successfully. Waiting for response...")
        
        # 等待一段时间，让Actor有时间处理消息
        import time
        time.sleep(5)
        
        logger.info("Test completed successfully.")
        
    except Exception as e:
        logger.error(f"Test failed with error: {e}")
        raise
    finally:
        # 关闭ActorSystem
        actor_system.shutdown()

if __name__ == "__main__":
    test_agent_actor()
