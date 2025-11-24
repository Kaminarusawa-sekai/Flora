"""执行连接器工厂类"""
from typing import Dict, Any, List
from .base_connector import BaseConnector


class ConnectorFactory:
    """
    执行连接器工厂，负责创建不同类型的执行连接器实例
    支持能力声明和查询
    """
    
    # 连接器注册表：{type: {"class": ConnectorClass, "capabilities": []}}
    _connectors = {} 
    
    @classmethod
    def register_connector(cls, connector_type: str, connector_class, capabilities: List[str] = None):
        """
        注册连接器类型，并声明其支持的能力
        
        Args:
            connector_type: 连接器类型标识
            connector_class: 连接器类
            capabilities: 连接器支持的能力列表
        """
        if capabilities is None:
            capabilities = []
        
        # 自动检测连接器实际实现的能力
        detected_capabilities = []
        
        # 检查基础能力 execute 是否实现
        if hasattr(connector_class, 'execute'):
            detected_capabilities.append('execute')
        
        # 检查可选能力是否实现（非默认实现）
        optional_capabilities = ['initialize', 'close', 'health_check', 'prepare', 'cancel', 'get_status']
        for cap in optional_capabilities:
            if hasattr(connector_class, cap):
                # 检查是否是自定义实现（不是BaseConnector的默认实现）
                base_method = getattr(BaseConnector, cap, None)
                connector_method = getattr(connector_class, cap)
                if base_method is None or connector_method is not base_method:
                    detected_capabilities.append(cap)
        
        # 合并显式声明和自动检测的能力
        all_capabilities = list(set(detected_capabilities + capabilities))
        
        cls._connectors[connector_type] = {
            "class": connector_class,
            "capabilities": all_capabilities
        }
    
    @classmethod
    def get_connector_capabilities(cls, connector_type: str) -> List[str]:
        """
        获取指定连接器类型支持的能力
        
        Args:
            connector_type: 连接器类型标识
            
        Returns:
            List[str]: 支持的能力列表
            
        Raises:
            ValueError: 当指定的连接器类型未注册时
        """
        if connector_type not in cls._connectors:
            raise ValueError(f"Unsupported connector type: {connector_type}")
        
        return cls._connectors[connector_type]["capabilities"]
    
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
            return cls._connectors[connector_type]["class"](config)
        
        raise ValueError(f"Unsupported connector type: {connector_type}")
    
    @classmethod
    def get_all_connectors(cls) -> Dict[str, Dict]:
        """
        获取所有注册的连接器信息
        
        Returns:
            Dict[str, Dict]: 包含所有连接器类型和其信息的字典
        """
        return cls._connectors.copy