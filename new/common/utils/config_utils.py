"""配置工具模块"""
import json
import os
import yaml
import logging
import configparser
from typing import Any, Dict, List, Optional, Union

from .logger import get_logger
from .json_utils import safe_json_dumps, safe_json_loads
from .error_handling import handle_exception, ErrorContext

logger = get_logger(__name__)

# 支持的配置文件扩展名
CONFIG_FILE_EXTENSIONS = {
    '.json': 'json',
    '.yml': 'yaml',
    '.yaml': 'yaml',
    '.ini': 'ini',
    '.cfg': 'ini',
    '.conf': 'ini'
}


def load_config(
    config_path: str,
    default_config: Optional[Dict[str, Any]] = None,
    encoding: str = 'utf-8'
) -> Dict[str, Any]:
    """
    加载配置文件
    自动识别配置文件格式（JSON、YAML、INI）
    
    Args:
        config_path: 配置文件路径
        default_config: 默认配置，如果文件不存在则返回此配置
        encoding: 文件编码
        
    Returns:
        配置字典
        
    Raises:
        FileNotFoundError: 如果文件不存在且未提供默认配置
        ValueError: 如果文件格式不支持或解析失败
    """
    # 检查文件是否存在
    if not os.path.exists(config_path):
        if default_config is not None:
            logger.warning(f"Config file not found: {config_path}, using default config")
            return default_config
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    # 获取文件扩展名
    _, ext = os.path.splitext(config_path)
    ext = ext.lower()
    
    # 识别文件类型
    config_type = CONFIG_FILE_EXTENSIONS.get(ext)
    if not config_type:
        raise ValueError(f"Unsupported config file format: {ext}")
    
    logger.info(f"Loading config from: {config_path} (type: {config_type})")
    
    try:
        with open(config_path, 'r', encoding=encoding) as f:
            if config_type == 'json':
                return json.load(f)
            elif config_type == 'yaml':
                return yaml.safe_load(f)
            elif config_type == 'ini':
                config = configparser.ConfigParser()
                config.read_file(f)
                # 转换为字典格式
                return {
                    section: dict(config.items(section))
                    for section in config.sections()
                }
    
    except (json.JSONDecodeError, yaml.YAMLError, configparser.Error) as e:
        logger.error(f"Failed to parse config file {config_path}: {str(e)}")
        raise ValueError(f"Failed to parse config file: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading config file {config_path}: {str(e)}")
        raise


def save_config(
    config_data: Dict[str, Any],
    config_path: str,
    indent: int = 2,
    encoding: str = 'utf-8',
    overwrite: bool = True
) -> None:
    """
    保存配置到文件
    自动根据文件扩展名确定格式
    
    Args:
        config_data: 配置数据
        config_path: 配置文件路径
        indent: 缩进空格数（仅用于JSON和YAML）
        encoding: 文件编码
        overwrite: 是否覆盖已存在的文件
        
    Raises:
        FileExistsError: 如果文件已存在且不允许覆盖
        ValueError: 如果文件格式不支持
        IOError: 如果写入失败
    """
    # 检查文件是否已存在
    if os.path.exists(config_path) and not overwrite:
        raise FileExistsError(f"Config file already exists: {config_path}")
    
    # 确保目录存在
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    
    # 获取文件扩展名
    _, ext = os.path.splitext(config_path)
    ext = ext.lower()
    
    # 识别文件类型
    config_type = CONFIG_FILE_EXTENSIONS.get(ext)
    if not config_type:
        raise ValueError(f"Unsupported config file format: {ext}")
    
    logger.info(f"Saving config to: {config_path} (type: {config_type})")
    
    try:
        with open(config_path, 'w', encoding=encoding) as f:
            if config_type == 'json':
                json.dump(config_data, f, indent=indent, ensure_ascii=False)
            elif config_type == 'yaml':
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            elif config_type == 'ini':
                config = configparser.ConfigParser()
                for section, options in config_data.items():
                    if isinstance(options, dict):
                        config[section] = options
                config.write(f)
    
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {str(e)}")
        raise


def merge_configs(
    base_config: Dict[str, Any],
    override_config: Dict[str, Any],
    deep_merge: bool = True
) -> Dict[str, Any]:
    """
    合并两个配置字典
    
    Args:
        base_config: 基础配置
        override_config: 覆盖配置
        deep_merge: 是否深度合并（递归合并嵌套字典）
        
    Returns:
        合并后的配置
    """
    # 创建基础配置的副本以避免修改原配置
    merged_config = base_config.copy()
    
    if not deep_merge:
        # 浅合并
        merged_config.update(override_config)
    else:
        # 深度合并
        for key, value in override_config.items():
            if key in merged_config and isinstance(merged_config[key], dict) and isinstance(value, dict):
                # 递归合并嵌套字典
                merged_config[key] = merge_configs(merged_config[key], value, deep_merge)
            else:
                # 直接覆盖
                merged_config[key] = value
    
    return merged_config


def get_config_value(
    config: Dict[str, Any],
    key_path: str,
    default: Any = None,
    delimiter: str = '.'
) -> Any:
    """
    从嵌套配置中获取值
    支持使用点号分隔的路径访问嵌套配置
    
    Args:
        config: 配置字典
        key_path: 键路径，如 "database.host"
        default: 默认值
        delimiter: 路径分隔符
        
    Returns:
        配置值或默认值
    """
    keys = key_path.split(delimiter)
    current = config
    
    try:
        for key in keys:
            current = current[key]
        return current
    except (KeyError, TypeError):
        return default


def set_config_value(
    config: Dict[str, Any],
    key_path: str,
    value: Any,
    delimiter: str = '.'
) -> Dict[str, Any]:
    """
    设置嵌套配置中的值
    支持使用点号分隔的路径设置嵌套配置
    
    Args:
        config: 配置字典
        key_path: 键路径，如 "database.host"
        value: 要设置的值
        delimiter: 路径分隔符
        
    Returns:
        更新后的配置字典
    """
    keys = key_path.split(delimiter)
    current = config
    
    # 遍历除最后一个键外的所有键
    for key in keys[:-1]:
        # 如果键不存在，创建空字典
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    
    # 设置最后一个键的值
    current[keys[-1]] = value
    
    return config


def validate_config(
    config: Dict[str, Any],
    required_keys: List[str],
    delimiter: str = '.'
) -> bool:
    """
    验证配置中是否包含所有必需的键
    
    Args:
        config: 配置字典
        required_keys: 必需的键路径列表
        delimiter: 路径分隔符
        
    Returns:
        是否包含所有必需的键
    """
    missing_keys = []
    
    for key_path in required_keys:
        if get_config_value(config, key_path, None, delimiter) is None:
            missing_keys.append(key_path)
    
    if missing_keys:
        logger.warning(f"Missing required config keys: {', '.join(missing_keys)}")
        return False
    
    return True


def find_config_file(
    config_name: str,
    search_paths: List[str],
    extensions: Optional[List[str]] = None
) -> Optional[str]:
    """
    在搜索路径中查找配置文件
    
    Args:
        config_name: 配置文件名（不含扩展名）
        search_paths: 搜索路径列表
        extensions: 要尝试的文件扩展名列表
        
    Returns:
        找到的配置文件路径或None
    """
    # 如果未指定扩展名，尝试所有支持的扩展名
    if not extensions:
        extensions = list(CONFIG_FILE_EXTENSIONS.keys())
    
    for path in search_paths:
        for ext in extensions:
            config_path = os.path.join(path, f"{config_name}{ext}")
            if os.path.exists(config_path):
                logger.info(f"Found config file: {config_path}")
                return config_path
    
    logger.warning(f"Config file '{config_name}' not found in any of the search paths")
    return None


def load_env_config(
    prefix: str = "",
    lowercase_keys: bool = True,
    parse_types: bool = True
) -> Dict[str, Any]:
    """
    从环境变量加载配置
    
    Args:
        prefix: 环境变量前缀
        lowercase_keys: 是否将键转换为小写
        parse_types: 是否自动解析数据类型
        
    Returns:
        配置字典
    """
    config = {}
    
    for key, value in os.environ.items():
        if key.startswith(prefix):
            # 移除前缀
            config_key = key[len(prefix):]
            # 转换为小写
            if lowercase_keys:
                config_key = config_key.lower()
            
            # 解析数据类型
            if parse_types:
                # 尝试解析为布尔值
                if value.lower() in ('true', 'yes', '1', 'on'):
                    value = True
                elif value.lower() in ('false', 'no', '0', 'off'):
                    value = False
                # 尝试解析为整数
                elif value.isdigit():
                    value = int(value)
                # 尝试解析为浮点数
                else:
                    try:
                        value = float(value)
                    except ValueError:
                        pass  # 保持字符串不变
            
            config[config_key] = value
    
    logger.info(f"Loaded {len(config)} config values from environment variables with prefix '{prefix}'")
    return config