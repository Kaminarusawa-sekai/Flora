"""
测试模块集成：验证拆分后的功能是否正常工作
"""
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 导入测试所需的模块
from external.database.redis_adapter import redis_adapter
from common.utils.actor_reference_manager import actor_reference_manager
from agents.router_actor import RouterActor
from agents.agent_registry import agent_registry


class TestModuleIntegration(unittest.TestCase):
    """测试模块集成功能"""
    
    @patch('new.external.database.redis_adapter.redis', create=True)
    @patch('new.external.database.redis_adapter.config_manager')
    def test_redis_adapter_initialization(self, mock_config_manager, mock_redis_module):
        """测试Redis连接适配器初始化"""
        # 模拟Redis客户端和模块
        mock_client = MagicMock()
        mock_redis = MagicMock(return_value=mock_client)
        mock_redis_module.Redis = mock_redis
        mock_redis_module.__version__ = '3.5.3'  # 模拟版本号
        
        # 模拟配置管理器
        mock_config_manager.get.return_value = {
            "host": "localhost",
            "port": 6379,
            "db": 0
        }
        
        # 创建一个新的RedisAdapter实例进行测试
        from external.database.redis_adapter import RedisAdapter
        # 确保全局REDIS_AVAILABLE为True
        from external.database import redis_adapter as redis_adapter_module
        redis_adapter_module.REDIS_AVAILABLE = True
        
        # 创建新实例
        adapter = RedisAdapter()
        
        # 验证初始化
        mock_redis.assert_called_once()
        
        # 测试获取客户端
        client = adapter.get_client()
        self.assertIsNotNone(client)
        
        # 测试Redis操作方法
        adapter.set_with_ttl('test_key', 'test_value', 10)
        mock_client.setex.assert_called_with('test_key', 10, 'test_value')
    
    def test_actor_reference_manager(self):
        """测试Actor引用管理器集成"""
        # 测试Redis键创建
        key = actor_reference_manager.create_redis_key('agent_actor', 'test_tenant', 'test_node')
        self.assertEqual(key, 'agent_actor:test_tenant:test_node')
        
        # 模拟一个简单的地址对象进行序列化测试
        class MockActorAddress:
            def __init__(self):
                self.host = 'localhost'
                self.port = 8000
                self.tenant_id = 'test_tenant'
                self.node_id = 'test_node'
            
            def __str__(self):
                return 'mock_actor_address'
        
        # 测试序列化/反序列化 - 由于实际的ActorAddress依赖Thespian，这里只做基本测试
        mock_address = MockActorAddress()
        serialized = actor_reference_manager.serialize_address(mock_address)
        self.assertIsNotNone(serialized)
        
        # 测试方法是否存在且可调用
        self.assertTrue(hasattr(actor_reference_manager, 'get_redis_client'))
        self.assertTrue(hasattr(actor_reference_manager, 'is_redis_available'))
        self.assertTrue(hasattr(actor_reference_manager, 'set_with_ttl'))
        self.assertTrue(hasattr(actor_reference_manager, 'get'))
        self.assertTrue(hasattr(actor_reference_manager, 'delete'))
        self.assertTrue(hasattr(actor_reference_manager, 'expire'))
    
    def test_router_actor_import(self):
        """测试RouterActor是否能正确导入和初始化"""
        # 验证RouterActor类是否存在
        self.assertIsNotNone(RouterActor)
        
        # 创建RouterActor实例（使用mock参数）
        with patch('new.agents.router_actor.actor_reference_manager'):
            router = RouterActor()
            self.assertIsNotNone(router)
    
    def test_agent_registry_integration(self):
        """测试AgentRegistry与新模块的集成"""
        # 验证AgentRegistry实例是否存在
        self.assertIsNotNone(agent_registry)
        
        # 验证agent_registry是否可以获取或创建AgentActor
        # 创建mock的RouterActor和ActorSystem
        mock_router = MagicMock()
        mock_system = MagicMock()
        
        # 设置RouterActor和ActorSystem
        agent_registry.router_actor = mock_router
        agent_registry.actor_system = mock_system
        
        # 测试get_or_create_agent_actor方法
        actor_ref = agent_registry.get_or_create_agent_actor('test_tenant', 'test_node')
        self.assertIsNotNone(actor_ref)
        
        # 测试agent_actor_context上下文管理器
        with agent_registry.agent_actor_context('test_tenant2', 'test_node2') as ctx_actor_ref:
            self.assertIsNotNone(ctx_actor_ref)
    
    def test_full_integration_flow(self):
        """测试完整的集成流程"""
        # 这个测试模拟了一个完整的使用流程
        # 1. 初始化RouterActor和AgentRegistry
        # 2. 获取或创建AgentActor
        # 3. 使用AgentActor
        # 4. 清理资源
        
        with patch('new.agents.router_actor.actor_reference_manager'), \
             patch('new.agents.agent_registry.TreeManager'):
            
            # 创建mock的RouterActor和ActorSystem
            mock_router = MagicMock()
            mock_system = MagicMock()
            
            # 设置RouterActor和ActorSystem
            agent_registry.router_actor = mock_router
            agent_registry.actor_system = mock_system
            
            # 获取或创建AgentActor
            actor_ref = agent_registry.get_or_create_agent_actor('integration_test', 'node1')
            
            # 模拟发送消息
            actor_ref.tell({'message': 'test_message'})
            
            # 验证消息是否通过RouterActor发送
            mock_system.tell.assert_called()


if __name__ == '__main__':
    unittest.main()
