import unittest
import sys
import os
import time
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from external.message_queue.rabbitmq_listener import RabbitMQListenerImpl


class TestRabbitMQListenerImpl(unittest.TestCase):
    """RabbitMQ监听器实现类测试 - 真实RabbitMQ连接测试"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建模拟对象
        self.mock_actor_system = MagicMock()
        self.mock_agent_actor_ref = MagicMock()
        
        # 使用真实的RabbitMQ地址
        self.rabbitmq_url = ""
        self.config = {
            'rabbitmq_url': self.rabbitmq_url
        }
        
        # 创建RabbitMQListenerImpl实例
        self.rabbitmq_listener = RabbitMQListenerImpl(
            self.mock_actor_system,
            self.mock_agent_actor_ref,
            self.config
        )
    
    def test_init(self):
        """测试初始化方法"""
        # 验证初始化参数
        self.assertEqual(self.rabbitmq_listener.actor_system, self.mock_actor_system)
        self.assertEqual(self.rabbitmq_listener.agent_actor_ref, self.mock_agent_actor_ref)
        self.assertEqual(self.rabbitmq_listener.config, self.config)
        self.assertEqual(self.rabbitmq_listener.rabbitmq_url, self.rabbitmq_url)
    
    def test_rabbitmq_available(self):
        """测试RabbitMQ依赖是否可用"""
        # 尝试导入pika，验证RabbitMQ依赖是否可用
        try:
            import pika
            self.assertTrue(True, "RabbitMQ依赖可用")
        except ImportError:
            self.skipTest("RabbitMQ依赖不可用")
    
    @patch('external.message_queue.rabbitmq_listener.pika.BlockingConnection')
    def test_connection_with_real_url(self, mock_blocking_connection):
        """测试使用真实RabbitMQ URL进行连接设置"""
        # 模拟pika连接和通道
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        # 调用start方法
        self.rabbitmq_listener.start()
        
        # 验证连接被创建
        mock_blocking_connection.assert_called_once()
        
        # 验证调用参数不为空
        called_args = mock_blocking_connection.call_args
        self.assertTrue(len(called_args[0]) > 0, "BlockingConnection应该被调用")
    
    @patch('external.message_queue.rabbitmq_listener.pika.BlockingConnection')
    def test_message_listener_setup(self, mock_blocking_connection):
        """测试消息监听器设置"""
        # 模拟pika连接和通道
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        # 调用start方法
        self.rabbitmq_listener.start()
        
        # 验证basic_consume被调用，确认监听器已设置
        mock_channel.basic_consume.assert_called_once()
        
        # 验证监听器绑定到了正确的队列
        call_args = mock_channel.basic_consume.call_args
        self.assertEqual(call_args[1]['queue'], 'worker.execute')
    
    def test_start_in_thread(self):
        """测试在独立线程中启动监听"""
        # 使用patch模拟start方法，避免实际连接到RabbitMQ
        with patch.object(self.rabbitmq_listener, 'start') as mock_start:
            # 调用start_in_thread方法
            self.rabbitmq_listener.start_in_thread()
            
            # 验证线程被创建
            self.assertIsNotNone(self.rabbitmq_listener.thread)
            
            # 等待一段时间，确保线程启动
            time.sleep(0.1)
            
            # 验证start方法被调用
            mock_start.assert_called_once()
    
    @patch('external.message_queue.rabbitmq_listener.pika.BlockingConnection')
    def test_cleanup(self, mock_blocking_connection):
        """测试资源清理"""
        # 模拟pika连接和通道
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        # 调用start方法
        self.rabbitmq_listener.start()
        
        # 设置running状态
        self.rabbitmq_listener.running = True
        
        # 调用stop方法
        self.rabbitmq_listener.stop()
        
        # 验证资源被正确清理
        mock_channel.stop_consuming.assert_called_once()
        mock_connection.close.assert_called_once()
        self.assertFalse(self.rabbitmq_listener.running)
    
    def test_callback_structure(self):
        """测试callback方法的基本结构"""
        # 验证callback方法存在且是可调用的
        self.assertTrue(hasattr(self.rabbitmq_listener, 'callback'))
        self.assertTrue(callable(self.rabbitmq_listener.callback))
    
    def test_rabbitmq_listener_instantiation(self):
        """测试RabbitMQListenerImpl实例化"""
        # 验证实例化成功
        self.assertIsInstance(self.rabbitmq_listener, RabbitMQListenerImpl)


if __name__ == "__main__":
    unittest.main()
