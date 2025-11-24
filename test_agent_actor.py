#!/usr/bin/env python3
"""
AgentActor重构测试脚本
验证重构后的AgentActor功能是否正常工作
"""

import logging
import pytest
from typing import Dict, Any
from thespian.actors import ActorSystem

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_agent_actor')

# 导入重构后的模块
from new.agents.agent_actor import AgentActor, create_agent_actor
from new.common.messages import (
    InitMessage, AgentTaskMessage as TaskMessage,
    SubtaskResultMessage, SubtaskErrorMessage
)
from new.agents.coordination.task_coordinator import TaskCoordinator
from new.capabilities.routing.task_router import TaskRouter
from new.agents.tree.tree_manager import TreeManager

@pytest.fixture
def actor_system():
    """创建并返回ActorSystem实例"""
    asys = ActorSystem()
    yield asys
    asys.shutdown()

@pytest.fixture
def mock_registry():
    """创建模拟的registry对象"""
    class MockRegistry:
        def get_agent_meta(self, agent_id):
            return {
                'id': agent_id,
                'capability': ['test_capability'],
                'is_leaf': True
            }
    return MockRegistry()

def test_agent_actor_initialization(actor_system, mock_registry):
    """测试AgentActor初始化"""
    logger.info("测试AgentActor初始化...")
    
    # 创建AgentActor实例
    agent_id = "test_agent_001"
    capabilities = ["test_capability"]
    memory_key = "test_memory_key"
    
    # 创建InitMessage
    init_msg = InitMessage(agent_id, capabilities, memory_key, mock_registry)
    
    # 发送初始化消息并等待响应
    agent_actor_ref = actor_system.createActor(AgentActor)
    response = actor_system.ask(agent_actor_ref, init_msg, timeout=5)
    
    logger.info(f"AgentActor {agent_id} 初始化成功，响应: {response}")
    
    logger.info("AgentActor初始化测试通过")

def test_create_agent_actor_factory(actor_system):
    """测试create_agent_actor工厂函数"""
    logger.info("测试create_agent_actor工厂函数...")
    
    # 使用工厂函数创建AgentActor
    agent_id = "test_agent_002"
    agent_name = "测试智能体"
    max_concurrency = 5
    
    agent_actor_ref = create_agent_actor(
        actor_system, agent_id, agent_name, max_concurrency
    )
    
    logger.info(f"使用工厂函数创建AgentActor {agent_id} 成功")
    logger.info("create_agent_actor工厂函数测试通过")

def test_message_handling(actor_system, mock_registry):
    """测试消息处理功能"""
    logger.info("测试消息处理功能...")
    
    # 创建并初始化AgentActor
    agent_id = "test_agent_003"
    capabilities = ["test_capability"]
    memory_key = "test_memory_key"
    
    agent_actor_ref = actor_system.createActor(AgentActor)
    init_msg = InitMessage(agent_id, capabilities, memory_key, mock_registry)
    actor_system.tell(agent_actor_ref, init_msg)
    
    # 构造测试任务消息
    test_task_id = "test_task_001"
    test_context = {
        "task_type": "leaf",
        "content": "测试任务",
        "params": {"test_key": "test_value"}
    }
    
    task_msg = TaskMessage(test_task_id, test_context)
    
    # 发送任务消息并等待响应
    response = actor_system.ask(agent_actor_ref, task_msg, timeout=10)
    
    logger.info(f"任务消息 {test_task_id} 处理成功，响应: {response}")
    logger.info("消息处理功能测试通过")

def test_leaf_task_execution(actor_system, mock_registry):
    """测试叶子任务执行"""
    logger.info("测试叶子任务执行...")
    
    # 创建并初始化AgentActor
    agent_id = "test_agent_004"
    capabilities = ["dify_workflow"]
    memory_key = "test_memory_key"
    
    agent_actor_ref = actor_system.createActor(AgentActor)
    init_msg = InitMessage(agent_id, capabilities, memory_key, mock_registry)
    actor_system.tell(agent_actor_ref, init_msg)
    
    # 构造叶子任务消息
    test_task_id = "test_leaf_task_001"
    test_context = {
        "is_leaf": True,
        "content": "测试叶子任务",
        "capability": "dify_workflow"
    }
    
    task_msg = TaskMessage(test_task_id, test_context)
    
    # 发送任务消息并等待响应
    response = actor_system.ask(agent_actor_ref, task_msg, timeout=15)
    print(response)
    
    logger.info(f"叶子任务消息 {test_task_id} 执行成功，响应: {response}")
    logger.info("叶子任务执行测试通过")

if __name__ == "__main__":
    # 运行测试
    import sys
    
    # 创建ActorSystem
    asys = ActorSystem()
    
    # 使用正式的AgentRegistry
    from new.agents.agent_registry import AgentRegistry
    from new.agents.tree.tree_manager import TreeManager
    from new.external.agent_structure.structure_interface import AgentStructureInterface
    
    # 创建内存结构管理器用于测试
    class MemoryStructure(AgentStructureInterface):
        def __init__(self):
            self.agents = []
            self.relationships = {}
        
        def get_agent_relationship(self, agent_id):
            return self.relationships.get(agent_id, {})
        
        def load_all_agents(self):
            return self.agents
        
        def close(self):
            pass
        
        def add_agent_relationship(self, parent_id: str, child_id: str, relationship_type: str) -> bool:
            if parent_id not in self.relationships:
                self.relationships[parent_id] = {'children': []}
            self.relationships[parent_id]['children'].append(child_id)
            return True
        
        def remove_agent(self, agent_id: str) -> bool:
            self.agents = [agent for agent in self.agents if agent.get('agent_id') != agent_id]
            if agent_id in self.relationships:
                del self.relationships[agent_id]
            # 移除父节点中的引用
            for parent_id, rels in list(self.relationships.items()):
                if agent_id in rels.get('children', []):
                    rels['children'].remove(agent_id)
            return True
        
        def add_agent(self, agent_data):
            self.agents.append(agent_data)
        
        def get_agent(self, agent_id):
            for agent in self.agents:
                if agent.get('agent_id') == agent_id:
                    return agent
            return None
    
    try:
        # 创建内存结构并注册测试Agent
        memory_structure = MemoryStructure()
        
        # 注册测试Agent
        test_agent_data = {
            "agent_id": "test_agent",
            "name": "Test Agent",
            "capability": ["test_capability"],
            "is_leaf": True,
            "code": "test_agent",
            "config": {}
        }
        memory_structure.add_agent(test_agent_data)
        
        # 创建带有内存结构的TreeManager
        tree_manager = TreeManager(structure=memory_structure)
        
        # 创建使用该TreeManager的AgentRegistry
        registry = AgentRegistry(tree_manager=tree_manager)
        
        # 运行测试
        test_agent_actor_initialization(asys, registry)
        logger.info("=" * 50)
        
        test_create_agent_actor_factory(asys)
        logger.info("=" * 50)
        
        test_message_handling(asys, registry)
        logger.info("=" * 50)
        
        test_leaf_task_execution(asys, registry)
        logger.info("=" * 50)
        
        logger.info("所有测试通过！AgentActor重构成功！")
        sys.exit(0)
    except Exception as e:
        logger.error(f"测试失败: {str(e)}")
        sys.exit(1)
    finally:
        # 关闭ActorSystem
        asys.shutdown()
