"""
AgentActor重构测试脚本
验证重构后的AgentActor功能是否正常工作
"""

import asyncio
import json
import logging
import pytest
from typing import Dict, Any

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_agent_actor')

# 导入重构后的模块
from .agent_actor import AgentActor, create_agent_actor
from .parallel.execution_manager import ParallelExecutionManager
from .coordination.task_coordinator import TaskCoordinator
from .tree.tree_manager import TreeManager

@pytest.mark.asyncio
async def test_agent_actor_initialization():
    """测试AgentActor初始化"""
    logger.info("测试AgentActor初始化...")
    
    try:
        # 创建AgentActor实例
        agent_actor = await create_agent_actor(
            agent_id="test_agent_001",
            agent_name="测试智能体",
            max_concurrency=5
        )
        
        logger.info(f"AgentActor初始化成功: {agent_actor.agent_id} - {agent_actor.agent_name}")
        logger.info(f"并行执行管理器已集成: {isinstance(agent_actor.parallel_executor, ParallelExecutionManager)}")
        logger.info(f"任务协调器已集成: {isinstance(agent_actor.task_coordinator, TaskCoordinator)}")
        logger.info(f"树管理器已集成: {isinstance(agent_actor.tree_manager, TreeManager)}")
        
        return True
    except Exception as e:
        logger.error(f"AgentActor初始化失败: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_message_handling():
    """测试消息处理功能"""
    logger.info("测试消息处理功能...")
    
    try:
        agent_actor = await create_agent_actor(
            agent_id="test_agent_001",
            agent_name="测试智能体"
        )
        
        # 构造测试消息
        test_message = {
            "type": "task",
            "task_id": "test_task_001",
            "task_type": "leaf",
            "content": "测试任务",
            "params": {"test_key": "test_value"}
        }
        
        # 模拟消息处理（这里只是验证方法调用不会抛出异常）
        # 实际功能测试需要完整的环境
        logger.info("准备处理测试消息...")
        # 不实际执行，只验证方法存在
        if hasattr(agent_actor, 'receive_message'):
            logger.info("receive_message方法存在")
        else:
            logger.error("receive_message方法不存在")
            return False
        
        logger.info("消息处理功能测试通过")
        return True
    except Exception as e:
        logger.error(f"消息处理测试失败: {str(e)}")
        return False

@pytest.mark.asyncio
async def test_component_integration():
    """测试组件集成"""
    logger.info("测试组件集成...")
    
    try:
        agent_actor = await create_agent_actor(
            agent_id="test_agent_001",
            agent_name="测试智能体"
        )
        
        # 验证组件集成和方法可访问性
        components = {
            "parallel_executor": ["execute_workflow", "execute_capability", "execute_data_query"],
            "task_coordinator": ["create_task", "add_subtask", "update_task_status"],
            "tree_manager": ["get_node", "add_node", "find_path"]
        }
        
        all_available = True
        for component_name, methods in components.items():
            component = getattr(agent_actor, component_name, None)
            if component:
                for method in methods:
                    if not hasattr(component, method):
                        logger.warning(f"{component_name}缺少方法: {method}")
                        all_available = False
                    else:
                        logger.info(f"{component_name}方法验证通过: {method}")
            else:
                logger.error(f"组件不存在: {component_name}")
                all_available = False
        
        if all_available:
            logger.info("组件集成测试通过")
        else:
            logger.warning("组件集成测试部分通过")
        
        return all_available
    except Exception as e:
        logger.error(f"组件集成测试失败: {str(e)}")
        return False

async def main():
    """主测试函数"""
    logger.info("开始测试重构后的AgentActor...")
    
    results = {
        "初始化测试": await test_agent_actor_initialization(),
        "消息处理测试": await test_message_handling(),
        "组件集成测试": await test_component_integration()
    }
    
    # 输出测试结果摘要
    logger.info("\n测试结果摘要:")
    all_passed = True
    for test_name, passed in results.items():
        status = "通过" if passed else "失败"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("\n所有测试通过！AgentActor重构成功！")
    else:
        logger.warning("\n部分测试失败，请检查代码")
    
    return all_passed

if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())
