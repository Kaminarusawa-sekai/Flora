"""执行连接接口及实现模块"""

from .base_connector import BaseConnector
from .connector_factory import ConnectorFactory
from .registry import connector_registry, ConnectorRegistry
from .scheduler import ConnectorScheduler

# 注册内置连接器
from .dify.connector import DifyConnector

# 注册Dify连接器
ConnectorFactory.register_connector('dify', DifyConnector)
connector_registry.register('dify', DifyConnector)

__all__ = ['BaseConnector', 'ConnectorFactory', 'ConnectorRegistry', 'connector_registry', 'ConnectorScheduler']
