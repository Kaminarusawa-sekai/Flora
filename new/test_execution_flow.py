"""测试代理执行流程"""
import asyncio
import sys
import os

# 将项目根目录添加到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from new.agents.agent_actor import AgentActor
from new.capability_actors.execution_actor import ExecutionActor
from new.common.messages import TaskMessage


async def test_agent_execution_flow():
    """测试代理执行流程"""
    print("=== 测试代理执行流程 ===")
    
    # 创建代理Actor和执行Actor
    agent_actor = AgentActor()
    execution_actor = ExecutionActor()
    
    try:
        # 启动Actor系统
        await agent_actor.start()
        await execution_actor.start()
        
        # 创建测试任务
        test_task = {
            "id": "test_task_123",
            "name": "测试计算任务",
            "capability_type": "data_processing",
            "capability_id": "calculate_total",
            "parameters": {
                "numbers": [1, 2, 3, 4, 5]
            },
            "parent_task_id": None,
            "is_leaf": True
        }
        
        # 发送任务给代理Actor
        task_message = TaskMessage(
            msg_type="task_request",
            task=test_task,
            sender=execution_actor.actor_id,
            receiver=agent_actor.actor_id,
            conversation_id="test_conversation_456"
        )
        
        print(f"发送测试任务给代理Actor: {task_message.msg_type}")
        
        # 这里应该有一个消息系统来发送消息，但为了简化测试，
        # 我们直接调用代理Actor的receiveMessage方法
        await agent_actor.receiveMessage(task_message)
        
        print("代理Actor已接收任务")
        
        # 模拟一些处理时间
        await asyncio.sleep(5)
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 停止Actor系统
        await agent_actor.stop()
        await execution_actor.stop()
        
    print("=== 测试完成 ===")


if __name__ == "__main__":
    asyncio.run(test_agent_execution_flow())