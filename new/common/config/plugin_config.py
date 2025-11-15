"""插件配置模块"""
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from ..utils.logger import get_logger
logger = get_logger(__name__)


class PluginConfig:
    """
    插件配置类
    用于加载和管理单个插件的配置
    """
    
    def __init__(self, plugin_name: str, config_path: Optional[str] = None):
        """
        初始化插件配置
        
        Args:
            plugin_name: 插件名称
            config_path: 插件配置文件路径
        """
        self.plugin_name = plugin_name
        self.config_path = config_path
        self._config: Dict[str, Any] = {}
        
        if config_path:
            self.load_config()
    
    def load_config(self) -> bool:
        """
        加载插件配置
        
        Returns:
            加载是否成功
        """
        if not self.config_path:
            logger.error(f"插件 {self.plugin_name} 配置路径未设置")
            return False
            
        config_path = Path(self.config_path)
        if not config_path.exists():
            logger.error(f"插件 {self.plugin_name} 配置文件不存在: {config_path}")
            return False
            
        try:
            if config_path.suffix in ['.yaml', '.yml']:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
            elif config_path.suffix == '.json':
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            elif config_path.suffix == '.env':
                from dotenv import load_dotenv
                load_dotenv(config_path)
                # 从环境变量加载配置
                self._config = {k: v for k, v in os.environ.items()}
            else:
                logger.error(f"插件 {self.plugin_name} 不支持的配置文件格式: {config_path.suffix}")
                return False
                
            logger.info(f"插件 {self.plugin_name} 配置加载成功: {config_path}")
            return True
        except Exception as e:
            logger.error(f"插件 {self.plugin_name} 配置加载失败: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键（支持多级键，如："database.host"）
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键（支持多级键，如："database.host"）
            value: 配置值
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
    
    def update(self, config: Dict[str, Any]) -> None:
        """
        更新配置
        
        Args:
            config: 新的配置字典
        """
        self._config.update(config)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            配置字典
        """
        return self._config.copy()
    
    def __getitem__(self, key: str) -> Any:
        """
        支持[]操作符获取配置
        """
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """
        支持[]操作符设置配置
        """
        self.set(key, value)


class PluginConfigManager:
    """
    插件配置管理器
    用于管理所有插件的配置
    """
    
    def __init__(self):
        self._plugin_configs: Dict[str, PluginConfig] = {}
    
    def register_plugin_config(self, plugin_config: PluginConfig) -> None:
        """
        注册插件配置
        
        Args:
            plugin_config: 插件配置实例
        """
        self._plugin_configs[plugin_config.plugin_name] = plugin_config
        logger.info(f"插件配置已注册: {plugin_config.plugin_name}")
    
    def get_plugin_config(self, plugin_name: str) -> Optional[PluginConfig]:
        """
        获取插件配置
        
        Args:
            plugin_name: 插件名称
            
        Returns:
            插件配置实例或None
        """
        return self._plugin_configs.get(plugin_name)
    
    def get(self, plugin_name: str, key: str, default: Any = None) -> Any:
        """
        获取指定插件的配置值
        
        Args:
            plugin_name: 插件名称
            key: 配置键
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        plugin_config = self._plugin_configs.get(plugin_name)
        if plugin_config:
            return plugin_config.get(key, default)
        return default
    
    def set(self, plugin_name: str, key: str, value: Any) -> None:
        """
        设置指定插件的配置值
        
        Args:
            plugin_name: 插件名称
            key: 配置键
            value: 配置值
        """
        plugin_config = self._plugin_configs.get(plugin_name)
        if plugin_config:
            plugin_config.set(key, value)
    
    def list_plugins(self) -> List[str]:
        """
        列出所有已注册的插件
        
        Returns:
            插件名称列表
        """
        return list(self._plugin_configs.keys())


# 插件配置管理器实例
plugin_config_manager = PluginConfigManager()
