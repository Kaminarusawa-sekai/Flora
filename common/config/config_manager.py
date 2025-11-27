"""配置管理器"""
import os
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from ..utils.singleton import Singleton
from ..utils.logger import get_logger
logger = get_logger(__name__)


class ConfigManager(Singleton):
    """
    配置管理器，用于加载和管理系统配置
    支持多环境配置和插件配置
    """
    
    def __init__(self):
        self._config: Dict[str, Any] = {}
        self._plugin_configs: Dict[str, Dict[str, Any]] = {}
        self._loaded_files: List[str] = []
    
    def load_config(self, config_path: str, environment: Optional[str] = None) -> None:
        """
        加载配置文件
        
        Args:
            config_path: 配置文件路径或目录
            environment: 环境名称（如：development, production）
        """
        config_path = Path(config_path)
        
        if config_path.is_file():
            self._load_single_file(config_path, environment)
        elif config_path.is_dir():
            for file in config_path.glob("*.yaml") + config_path.glob("*.yml"):
                self._load_single_file(file, environment)
        else:
            logger.warning(f"配置路径不存在: {config_path}")
    
    def _load_single_file(self, file_path: Path, environment: Optional[str] = None) -> None:
        """
        加载单个配置文件
        
        Args:
            file_path: 配置文件路径
            environment: 环境名称
        """
        if str(file_path) in self._loaded_files:
            return  # 已加载过该文件，跳过
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                
            if config_data:
                # 如果指定了环境，只加载对应环境的配置
                if environment and isinstance(config_data, dict):
                    env_config = config_data.get(environment, {})
                    if env_config:
                        self._config.update(env_config)
                else:
                    self._config.update(config_data)
                    
                self._loaded_files.append(str(file_path))
                logger.info(f"配置文件加载成功: {file_path}")
        except Exception as e:
            logger.error(f"加载配置文件失败 {file_path}: {str(e)}")
    
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
    
    def load_plugin_config(self, plugin_name: str, config: Dict[str, Any]) -> None:
        """
        加载插件配置
        
        Args:
            plugin_name: 插件名称
            config: 插件配置
        """
        self._plugin_configs[plugin_name] = config
        logger.info(f"插件配置加载成功: {plugin_name}")
    
    def get_plugin_config(self, plugin_name: str, default: Any = None) -> Dict[str, Any]:
        """
        获取插件配置
        
        Args:
            plugin_name: 插件名称
            default: 默认值
            
        Returns:
            插件配置或默认值
        """
        return self._plugin_configs.get(plugin_name, default)
    
    def clear(self) -> None:
        """清除所有配置"""
        self._config.clear()
        self._plugin_configs.clear()
        self._loaded_files.clear()
        logger.info("所有配置已清除")


# 配置管理器实例
config_manager = ConfigManager()
