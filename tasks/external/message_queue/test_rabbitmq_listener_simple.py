import unittest
import json
import sys
import os
import time
from unittest.mock import MagicMock, patch, call

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from external.message_queue.rabbitmq_listener import RabbitMQListenerImpl


class TestRabbitMQListenerImpl(unittest.TestCase):
    """RabbitMQ监听器实现类测试 - 简化版"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建模拟对象
        self.mock_actor_system = MagicMock()
        self.mock_agent_actor_ref = MagicMock()
        self.config = {
            'rabbitmq_url': 'amqp://guest:guest@localhost:5672/'
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
        self.assertEqual(self.rabbitmq_listener.rabbitmq_url, self.config['rabbitmq_url'])
    
    def test_callback(self):
        """测试callback方法能够被正确调用"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 1
        mock_properties = MagicMock()
        
        # 简单的消息体
        message_body = b'{"msg_type": "START_TASK"}'
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证basic_ack被调用（表示消息被处理）
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=1)
    
    def test_callback_invalid_json(self):
        """测试callback方法处理无效的JSON数据"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 2
        mock_properties = MagicMock()
        
        # 无效的JSON数据
        message_body = b"invalid json data"
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证basic_nack被调用（表示消息处理失败）
        mock_ch.basic_nack.assert_called_once_with(delivery_tag=2, requeue=False)
    
    @patch('external.message_queue.rabbitmq_listener.pika.BlockingConnection')
    def test_start(self, mock_blocking_connection):
        """测试start方法能够正确初始化连接并开始监听"""
        # 模拟pika连接和通道
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        # 调用start方法
        self.rabbitmq_listener.start()
        
        # 验证连接被创建
        mock_blocking_connection.assert_called_once()
        mock_connection.channel.assert_called_once()
        
        # 验证exchange_declare被调用
        mock_channel.exchange_declare.assert_called_once()
        
        # 验证queue_declare被调用
        mock_channel.queue_declare.assert_called_once()
        
        # 验证queue_bind被调用
        mock_channel.queue_bind.assert_called_once()
        
        # 验证basic_consume被调用，确认callback被注册
        mock_channel.basic_consume.assert_called_once()
        # 验证callback函数被传递给basic_consume
        call_args = mock_channel.basic_consume.call_args
        self.assertEqual(call_args[1]['on_message_callback'], self.rabbitmq_listener.callback)
    
    @patch('external.message_queue.rabbitmq_listener.pika.BlockingConnection')
    def test_stop(self, mock_blocking_connection):
        """测试stop方法能够正确停止监听"""
        # 模拟pika连接和通道
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        # 调用start方法启动监听
        self.rabbitmq_listener.start()
        
        # 设置running为True
        self.rabbitmq_listener.running = True
        
        # 调用stop方法
        self.rabbitmq_listener.stop()
        
        # 验证stop_consuming被调用
        mock_channel.stop_consuming.assert_called_once()
        
        # 验证connection.close被调用
        mock_connection.close.assert_called_once()
        
        # 验证running被设置为False
        self.assertFalse(self.rabbitmq_listener.running)
    
    def test_start_in_thread(self):
        """测试start_in_thread方法能够在独立线程中启动监听"""
        # 使用patch模拟start方法，避免实际启动RabbitMQ连接
        with patch.object(self.rabbitmq_listener, 'start') as mock_start:
            # 调用start_in_thread方法
            self.rabbitmq_listener.start_in_thread()
            
            # 验证thread被创建
            self.assertIsNotNone(self.rabbitmq_listener.thread)
            
            # 等待线程完成
            self.rabbitmq_listener.thread.join(timeout=1.0)
            
            # 验证start方法被调用
            mock_start.assert_called_once()
    
    def test_callback_with_real_message_structure(self):
        """测试callback方法处理真实的消息结构"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 3
        mock_properties = MagicMock()
        
        # 模拟真实的RabbitMQ消息结构
        message_data = {
            "msg_type": "START_TASK",
            "task_id": "test-task-123",
            "user_input": "test input",
            "user_id": "test-user"
        }
        message_body = json.dumps(message_data).encode('utf-8')
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证消息被确认（basic_ack被调用）
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=3)
    
    @patch('external.message_queue.rabbitmq_listener.pika.BlockingConnection')
    def test_message_flow(self, mock_blocking_connection):
        """测试完整的消息流程：接收消息 -> 调用callback -> 确认消息"""
        # 模拟pika连接和通道
        mock_connection = MagicMock()
        mock_channel = MagicMock()
        mock_blocking_connection.return_value = mock_connection
        mock_connection.channel.return_value = mock_channel
        
        # 调用start方法启动监听
        self.rabbitmq_listener.start()
        
        # 模拟接收到消息
        mock_ch = mock_channel
        mock_method = MagicMock()
        mock_method.delivery_tag = 4
        mock_properties = MagicMock()
        message_body = b'{"msg_type": "START_TASK"}'
        
        # 模拟channel.basic_consume注册的callback被调用
        # 从basic_consume的调用参数中获取实际注册的callback
        registered_callback = mock_channel.basic_consume.call_args[1]['on_message_callback']
        
        # 调用注册的callback
        registered_callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证消息被确认
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=4)


if __name__ == "__main__":
    unittest.main()
