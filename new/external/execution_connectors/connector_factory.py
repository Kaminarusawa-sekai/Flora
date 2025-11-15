"""执行连接器工厂类"""
from typing import Dict, Any
from .base_connector import BaseConnector


class ConnectorFactory:
    """
    执行连接器工厂，负责创建不同类型的执行连接器实例
    """
    
    _connectors = {}
    
    @classmethod
    def register_connector(cls, connector_type: str, connector_class):
        """
        注册连接器类型
        
        Args:
            connector_type: 连接器类型标识
            connector_class: 连接器类
        """
        cls._connectors[connector_type] = connector_class
    
    @classmethod
    def create_connector(cls, connector_type: str, config: Dict[str, Any]) -> BaseConnector:
        """
        创建连接器实例
        
        Args:
            connector_type: 连接器类型
            config: 连接器配置
            
        Returns:
            BaseConnector: 连接器实例
            
        Raises:
            ValueError: 当指定的连接器类型不支持时
        """
        if connector_type == 'dify':
            # 延迟导入以避免循环依赖
            from .dify.connector import DifyConnector
            return DifyConnector(config)
        
        if connector_type in cls._connectors:
            return cls._connectors[connector_type](config)
        
        raise ValueError(f"Unsupported connector type: {connector_type}")
