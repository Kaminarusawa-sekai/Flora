"""
RouterActor引用管理机制测试

测试中心化路由Actor和外部注册表机制的核心功能，
包括唯一性保障、心跳机制和引用管理。
"""

import unittest
import time
from unittest.mock import patch, MagicMock
from thespian.actors import ActorAddress

# 导入需要测试的模块
from ..router_actor import RouterActor, SessionActor, UserRequest
from ..actor_reference_utils import actor_reference_utils


class TestUserRequest(unittest.TestCase):
    """测试UserRequest类"""
    
    def test_user_request_creation(self):
        """测试UserRequest创建和属性"""
        tenant_id = "test_tenant"
        node_id = "test_node"
        req = UserRequest(tenant_id, node_id)
        
        self.assertEqual(req.tenant_id, tenant_id)
        self.assertEqual(req.node_id, node_id)


class TestRouterActor(unittest.TestCase):
    """测试RouterActor类"""
    
    def setUp(self):
        """测试前设置"""
        # 创建一个模拟的ActorSystem环境
        self.router = RouterActor()
        self.router.logger = MagicMock()
        self.router.createActor = MagicMock()
        self.router.send = MagicMock()
        
        # 模拟Redis连接
        with patch('..actor_reference_utils.actor_reference_utils') as mock_utils:
            self.mock_utils = mock_utils
            self.mock_utils.get.return_value = None
            self.mock_utils.set_with_ttl.return_value = True
            self.mock_utils.delete.return_value = True
            self.mock_utils.expire.return_value = True
    
    def test_handle_user_request_new_session(self):
        """测试处理用户请求时创建新会话"""
        # 模拟没有现有会话
        self.mock_utils.get.return_value = None
        
        # 创建模拟的Actor地址
        mock_session_addr = MagicMock(spec=ActorAddress)
        self.router.createActor.return_value = mock_session_addr
        
        # 创建测试请求
        tenant_id = "test_tenant"
        node_id = "test_node"
        request = UserRequest(tenant_id, node_id)
        sender = MagicMock(spec=ActorAddress)
        
        # 调用处理方法
        with patch('..actor_reference_utils.actor_reference_utils') as mock_utils:
            mock_utils.get.return_value = None
            mock_utils.set_with_ttl.return_value = True
            self.router._handle_user_request(request, sender)
        
        # 验证创建了SessionActor
        self.router.createActor.assert_called_once_with(SessionActor)
        
        # 验证注册到了Redis
        expected_key = f"session:{tenant_id}:{node_id}"
        mock_utils.set_with_ttl.assert_called_once()
        
        # 验证发送了消息
        self.router.send.assert_called_once()
    
    def test_handle_user_request_existing_session(self):
        """测试处理用户请求时使用现有会话"""
        # 模拟有现有会话
        mock_addr_str = "mock_actor_address"
        self.mock_utils.get.return_value = mock_addr_str
        
        # 模拟反序列化
        mock_session_addr = MagicMock(spec=ActorAddress)
        self.mock_utils.deserialize_address.return_value = mock_session_addr
        
        # 创建测试请求
        tenant_id = "test_tenant"
        node_id = "test_node"
        request = UserRequest(tenant_id, node_id)
        sender = MagicMock(spec=ActorAddress)
        
        # 调用处理方法
        with patch('..actor_reference_utils.actor_reference_utils') as mock_utils:
            mock_utils.get.return_value = mock_addr_str
            mock_utils.deserialize_address.return_value = mock_session_addr
            self.router._handle_user_request(request, sender)
        
        # 验证没有创建新的SessionActor
        self.router.createActor.assert_not_called()
        
        # 验证反序列化了地址
        mock_utils.deserialize_address.assert_called_once_with(mock_addr_str)
        
        # 验证转发了消息
        self.router.send.assert_called_once_with(mock_session_addr, request)
    
    def test_handle_refresh_ttl(self):
        """测试处理TTL刷新"""
        tenant_id = "test_tenant"
        node_id = "test_node"
        msg = {"tenant_id": tenant_id, "node_id": node_id}
        
        # 调用刷新方法
        with patch('..actor_reference_utils.actor_reference_utils') as mock_utils:
            mock_utils.create_redis_key.return_value = f"session:{tenant_id}:{node_id}"
            mock_utils.expire.return_value = True
            
            # 设置内存字典
            self.router._memory_dict = {}
            
            self.router._handle_refresh_ttl(msg)
        
        # 验证刷新了TTL
        mock_utils.expire.assert_called_once()


class TestSessionActor(unittest.TestCase):
    """测试SessionActor类"""
    
    def setUp(self):
        """测试前设置"""
        # 创建一个模拟的SessionActor
        self.session = SessionActor()
        self.session.logger = MagicMock()
        self.session.createActor = MagicMock()
        self.session.send = MagicMock()
        self.session.stopActor = MagicMock()
    
    @patch('..router_actor.AgentActor')
    def test_initialize(self, mock_agent_actor):
        """测试初始化SessionActor"""
        tenant_id = "test_tenant"
        node_id = "test_node"
        router_ref = MagicMock(spec=ActorAddress)
        
        # 创建模拟的AgentActor引用
        mock_agent_ref = MagicMock()
        self.session.createActor.return_value = mock_agent_ref
        
        # 创建初始化消息
        init_msg = {
            "message_type": "initialize",
            "tenant_id": tenant_id,
            "node_id": node_id
        }
        
        # 调用初始化
        self.session._initialize(init_msg, router_ref)
        
        # 验证属性设置正确
        self.assertEqual(self.session.tenant_id, tenant_id)
        self.assertEqual(self.session.node_id, node_id)
        self.assertEqual(self.session.router_ref, router_ref)
        self.assertEqual(self.session.agent_actor, mock_agent_ref)
        
        # 验证创建了AgentActor
        self.session.createActor.assert_called_once()
        
        # 验证注册到了Router
        self.session.send.assert_called_once_with(router_ref, {
            "message_type": "register_actor",
            "tenant_id": tenant_id,
            "node_id": node_id
        })
    
    def test_heartbeat_mechanism(self):
        """测试心跳机制（简化版，不实际启动线程）"""
        tenant_id = "test_tenant"
        node_id = "test_node"
        self.session.tenant_id = tenant_id
        self.session.node_id = node_id
        self.session.router_ref = MagicMock(spec=ActorAddress)
        self.session._should_run_heartbeat = False  # 防止线程实际运行
        
        # 调用发送心跳方法
        self.session._send_heartbeat()
        
        # 验证发送了心跳消息
        self.session.send.assert_called_once()
        args, _ = self.session.send.call_args
        self.assertEqual(args[0], self.session.router_ref)
        self.assertEqual(args[1]["message_type"], "heartbeat")
        self.assertEqual(args[1]["tenant_id"], tenant_id)
        self.assertEqual(args[1]["node_id"], node_id)
    
    def test_refresh_ttl(self):
        """测试刷新TTL"""
        tenant_id = "test_tenant"
        node_id = "test_node"
        self.session.tenant_id = tenant_id
        self.session.node_id = node_id
        self.session.router_ref = MagicMock(spec=ActorAddress)
        
        # 调用刷新TTL方法
        self.session._refresh_ttl()
        
        # 验证发送了刷新消息
        self.session.send.assert_called_once_with(self.session.router_ref, {
            "message_type": "refresh_ttl",
            "tenant_id": tenant_id,
            "node_id": node_id
        })


class TestActorReferenceUtils(unittest.TestCase):
    """测试Actor引用工具类"""
    
    @patch('redis.Redis')
    def test_serialize_deserialize(self, mock_redis):
        """测试序列化和反序列化Actor地址"""
        # 创建模拟的Actor地址
        mock_address = MagicMock(spec=ActorAddress)
        mock_address.__str__.return_value = "mock_actor_address"
        
        # 序列化
        serialized = actor_reference_utils.serialize_address(mock_address)
        self.assertIsInstance(serialized, str)
        
        # 注意：这里只是验证序列化返回了字符串，
        # 实际的反序列化需要Thespian的ActorAddress.from_hash()方法
        # 在实际测试环境中应该使用真实的ActorAddress实例


if __name__ == '__main__':
    unittest.main()
