"""配置管理模块"""
from .config_manager import ConfigManager, config_manager
from .plugin_config import PluginConfig, PluginConfigManager, plugin_config_manager

__all__ = [
    "ConfigManager",
    "config_manager",
    "PluginConfig",
    "PluginConfigManager",
    "plugin_config_manager"
]

__version__ = "1.0.0"
__author__ = "Flora Team"
