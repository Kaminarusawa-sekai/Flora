import unittest
import sys
import os
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../../')))

from external.message_queue.rabbitmq_listener import RabbitMQListenerImpl


class TestRabbitMQListenerImpl(unittest.TestCase):
    """RabbitMQ监听器实现类测试 - 极简版"""
    
    def setUp(self):
        """测试前的准备工作"""
        # 创建模拟对象
        self