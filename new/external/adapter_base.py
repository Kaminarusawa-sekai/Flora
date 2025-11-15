"""适配器基类定义"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class AdapterBase(ABC):
    """
    所有适配器的基类，提供通用接口和生命周期管理
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化适配器
        
        Args:
            config: 适配器配置参数
        """
        self.config = config or {}
        self.is_initialized = False
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化适配器
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭适配器，释放资源
        """
        pass
    
    def get_config_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键名
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        return self.config.get(key, default)
    
    def validate_config(self, required_keys: list) -> bool:
        """
        验证配置是否包含必需的键
        
        Args:
            required_keys: 必需的配置键列表
            
        Returns:
            bool: 配置是否有效
        """
        return all(key in self.config for key in required_keys)
