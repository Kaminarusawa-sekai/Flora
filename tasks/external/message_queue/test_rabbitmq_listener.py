import unittest
import json
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from unittest.mock import MagicMock, patch
from external.message_queue.rabbitmq_listener import RabbitMQListenerImpl
from common.messages.task_messages import AgentTaskMessage, ResumeTaskMessage


class TestRabbitMQListenerImpl(unittest.TestCase):
    """RabbitMQ监听器实现类测试"""
    
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
        self.assertIsNone(self.rabbitmq_listener.connection)
        self.assertIsNone(self.rabbitmq_listener.channel)
        self.assertIsNone(self.rabbitmq_listener.thread)
    
    def test_callback_start_task_new_format(self):
        """测试callback方法处理新格式的START_TASK消息"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 1
        mock_properties = MagicMock()
        
        # 新格式消息
        message_data = {
            "msg_type": "START_TASK",
            "instance_id": "test-instance-123",
            "definition_id": "test-definition-456",
            "trace_id": "test-trace-789",
            "input_params": {"param1": "value1", "param2": "value2"},
            "user_id": "test-user"
        }
        message_body = json.dumps(message_data).encode('utf-8')
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证actor_system.tell被调用，并且传递了正确的消息
        self.mock_actor_system.tell.assert_called_once()
        called_args = self.mock_actor_system.tell.call_args
        self.assertEqual(called_args[0][0], self.mock_agent_actor_ref)
        self.assertIsInstance(called_args[0][1], AgentTaskMessage)
        
        # 验证消息内容
        actor_msg = called_args[0][1]
        self.assertEqual(actor_msg.task_id, "test-instance-123")
        self.assertEqual(actor_msg.user_id, "test-user")
        self.assertEqual(actor_msg.user_input["instance_id"], "test-instance-123")
        self.assertEqual(actor_msg.user_input["definition_id"], "test-definition-456")
        self.assertEqual(actor_msg.user_input["trace_id"], "test-trace-789")
        self.assertEqual(actor_msg.user_input["input_params"], {"param1": "value1", "param2": "value2"})
        
        # 验证basic_ack被调用
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=1)
    
    def test_callback_start_task_old_format(self):
        """测试callback方法处理旧格式的START_TASK消息"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 2
        mock_properties = MagicMock()
        
        # 旧格式消息
        message_data = {
            "msg_type": "START_TASK",
            "task_id": "test-task-123",
            "user_input": {"key": "value"},
            "user_id": "test-user"
        }
        message_body = json.dumps(message_data).encode('utf-8')
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证actor_system.tell被调用，并且传递了正确的消息
        self.mock_actor_system.tell.assert_called_once()
        called_args = self.mock_actor_system.tell.call_args
        self.assertEqual(called_args[0][0], self.mock_agent_actor_ref)
        self.assertIsInstance(called_args[0][1], AgentTaskMessage)
        
        # 验证消息内容
        actor_msg = called_args[0][1]
        self.assertEqual(actor_msg.task_id, "test-task-123")
        self.assertEqual(actor_msg.user_id, "test-user")
        self.assertEqual(actor_msg.user_input, {"key": "value"})
        
        # 验证basic_ack被调用
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=2)
    
    def test_callback_resume_task(self):
        """测试callback方法处理RESUME_TASK消息"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 3
        mock_properties = MagicMock()
        
        # RESUME_TASK消息
        message_data = {
            "msg_type": "RESUME_TASK",
            "task_id": "test-task-123",
            "parameters": {"param1": "value1"},
            "user_id": "test-user"
        }
        message_body = json.dumps(message_data).encode('utf-8')
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证actor_system.tell被调用，并且传递了正确的消息
        self.mock_actor_system.tell.assert_called_once()
        called_args = self.mock_actor_system.tell.call_args
        self.assertEqual(called_args[0][0], self.mock_agent_actor_ref)
        self.assertIsInstance(called_args[0][1], ResumeTaskMessage)
        
        # 验证消息内容
        actor_msg = called_args[0][1]
        self.assertEqual(actor_msg.task_id, "test-task-123")
        self.assertEqual(actor_msg.user_id, "test-user")
        self.assertEqual(actor_msg.parameters, {"param1": "value1"})
        
        # 验证basic_ack被调用
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=3)
    
    def test_callback_unknown_msg_type(self):
        """测试callback方法处理未知消息类型"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 4
        mock_properties = MagicMock()
        
        # 未知消息类型
        message_data = {
            "msg_type": "UNKNOWN_TYPE",
            "task_id": "test-task-123"
        }
        message_body = json.dumps(message_data).encode('utf-8')
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证actor_system.tell没有被调用
        self.mock_actor_system.tell.assert_not_called()
        
        # 验证basic_ack被调用
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=4)
    
    def test_callback_default_msg_type(self):
        """测试callback方法处理没有指定msg_type的消息（默认使用START_TASK）"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 5
        mock_properties = MagicMock()
        
        # 没有msg_type的消息
        message_data = {
            "task_id": "test-task-123",
            "user_input": {"key": "value"},
            "user_id": "test-user"
        }
        message_body = json.dumps(message_data).encode('utf-8')
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证actor_system.tell被调用，并且传递了正确的消息
        self.mock_actor_system.tell.assert_called_once()
        called_args = self.mock_actor_system.tell.call_args
        self.assertIsInstance(called_args[0][1], AgentTaskMessage)
        
        # 验证basic_ack被调用
        mock_ch.basic_ack.assert_called_once_with(delivery_tag=5)
    
    def test_callback_invalid_json(self):
        """测试callback方法处理无效的JSON数据"""
        # 模拟消息数据
        mock_ch = MagicMock()
        mock_method = MagicMock()
        mock_method.delivery_tag = 6
        mock_properties = MagicMock()
        
        # 无效的JSON数据
        message_body = b"invalid json data"
        
        # 调用callback方法
        self.rabbitmq_listener.callback(mock_ch, mock_method, mock_properties, message_body)
        
        # 验证actor_system.tell没有被调用
        self.mock_actor_system.tell.assert_not_called()
        
        # 验证basic_nack被调用
        mock_ch.basic_nack.assert_called_once_with(delivery_tag=6, requeue=False)
    
    @patch('external.message_queue.rabbitmq_listener.pika.BlockingConnection')
    def test_start(self, mock_blocking_connection):
        """测试start方法"""
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
        mock_channel.exchange_declare.assert_called_once_with(
            exchange='worker.execute',
            type='direct',
            durable=True
        )
        
        # 验证queue_declare被调用
        mock_channel.queue_declare.assert_called_once_with(
            queue='worker.execute',
            durable=True
        )
        
        # 验证queue_bind被调用
        mock_channel.queue_bind.assert_called_once_with(
            queue='worker.execute',
            exchange='worker.execute',
            routing_key='worker.execute'
        )
        
        # 验证basic_consume被调用
        mock_channel.basic_consume.assert_called_once()
    
    @patch('external.message_queue.rabbitmq_listener.pika.BlockingConnection')
    def test_stop(self, mock_blocking_connection):
        """测试stop方法"""
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
        """测试start_in_thread方法"""
        # 使用patch模拟start方法，避免实际启动RabbitMQ连接
        with patch.object(self.rabbitmq_listener, 'start') as mock_start:
            # 调用start_in_thread方法
            self.rabbitmq_listener.start_in_thread()
            
            # 验证thread被创建并且start被调用
            self.assertIsNotNone(self.rabbitmq_listener.thread)
            self.rabbitmq_listener.thread.join(timeout=1.0)  # 等待线程完成
            mock_start.assert_called_once()


if __name__ == "__main__":
    unittest.main()
