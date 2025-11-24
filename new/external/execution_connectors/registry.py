"""连接器注册表模块"""
from typing import Dict, List, Any, Type
from .base_connector import BaseConnector


class ConnectorRegistry:
    """
    连接器注册表，用于管理连接器类型及其支持的能力
    
    实现能力自适应的统一契约：
    1. 连接器注册时声明支持的能力
    2. 自动检测连接器实际实现的能力
    3. 提供能力查询接口
    """
    
    def __init__(self):
        self._registry: Dict[str, Dict[str, Any]] = {}
    
    def register(self, connector_type: str, connector_class: Type[BaseConnector], capabilities: List[str] = None) -> None:
        """
        注册连接器类型
        
        Args:
            connector_type: 连接器类型标识
            connector_class: 连接器类
            capabilities: 显式声明的能力列表
        """
        if capabilities is None:
            capabilities = []
        
        # 自动检测连接器实现的能力
        detected_capabilities = self._detect_capabilities(connector_class)
        
        # 合并显式声明和自动检测的能力
        all_capabilities = list(set(detected_capabilities + capabilities))
        
        self._registry[connector_type] = {
            "class": connector_class,
            "capabilities": all_capabilities
        }
    
    def _detect_capabilities(self, connector_class: Type[BaseConnector]) -> List[str]:
        """
        自动检测连接器类实现的能力
        
        Args:
            connector_class: 连接器类
            
        Returns:
            检测到的能力列表
        """
        capabilities = []
        
        # 检查基础能力 execute 是否实现
        if hasattr(connector_class, 'execute'):
            capabilities.append('execute')
        
        # 检查可选能力是否实现（非默认实现）
        optional_capabilities = ['initialize', 'close', 'health_check', 'prepare', 'cancel', 'get_status']
        for cap in optional_capabilities:
            if hasattr(connector_class, cap):
                # 检查是否是自定义实现（不是BaseConnector的默认实现）
                base_method = getattr(BaseConnector, cap, None)
                connector_method = getattr(connector_class, cap)
                if base_method is None or connector_method is not base_method:
                    capabilities.append(cap)
        
        return capabilities
    
    def get_capabilities(self, connector_type: str) -> List[str]:
        """
        获取指定连接器类型支持的能力
        
        Args:
            connector_type: 连接器类型标识
            
        Returns:
            支持的能力列表
        """
        if connector_type not in self._registry:
            raise ValueError(f"Connector type '{connector_type}' not registered")
        
        return self._registry[connector_type]["capabilities"]
    
    def has_capability(self, connector_type: str, capability: str) -> bool:
        """
        检查连接器类型是否支持特定能力
        
        Args:
            connector_type: 连接器类型标识
            capability: 能力名称
            
        Returns:
            是否支持该能力
        """
        if connector_type not in self._registry:
            return False
        
        return capability in self._registry[connector_type]["capabilities"]
    
    def get_all_connectors(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有注册的连接器信息
        
        Returns:
            包含所有连接器类型和其信息的字典
        """
        return self._registry.copy()
    
    def get_connector_class(self, connector_type: str) -> Type[BaseConnector]:
        """
        获取指定连接器类型的类
        
        Args:
            connector_type: 连接器类型标识
            
        Returns:
            连接器类
        """
        if connector_type not in self._registry:
            raise ValueError(f"Connector type '{connector_type}' not registered")
        
        return self._registry[connector_type]["class"]

    def create_connector(self, connector_type: str, config: Dict[str, Any]) -> BaseConnector:
        """
        创建连接器实例
        
        Args:
            connector_type: 连接器类型标识
            config: 连接器配置
            
        Returns:
            连接器实例
        """
        return self.get_connector_class(connector_type)(config)


# 创建全局注册表实例
connector_registry = ConnectorRegistry()
