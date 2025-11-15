"""工具函数模块"""
# 现有导入
from .logger import get_logger, LoggerConfig, set_global_log_level, log_with_context, log_error_with_traceback
from .singleton import Singleton, LazySingleton, ThreadLocalSingleton
from .json_utils import safe_json_dumps, safe_json_loads
from .time_utils import format_time, get_current_timestamp
from .error_handling import retry_decorator, handle_exception, ErrorContext, safe_execute
from .config_utils import load_config, save_config
from .data_validation import validate_input, validate_schema

# 新添加的导入
from .cache import Cache, LRUCache, MemoryCache, TTLCache, CacheEntry, CacheStats, cache, invalidate_cache
from .resource_manager import ResourceManager, ResourcePool, global_resource_manager
from .serializer import to_json, from_json, to_pickle, from_pickle, to_yaml, from_yaml, serialize, deserialize, register_serializer
from .validator import (
    ValidationResult,
    Validator,
    NotEmptyValidator,
    TypeValidator,
    StringValidator,
    NumberValidator,
    ListValidator,
    DictValidator,
    DateTimeValidator,
    EnumValidator,
    EmailValidator,
    URLValidator,
    CustomValidator,
    CompositeValidator,
    ValidationSchema,
    ValidatorRegistry,
    global_validator_registry
)

__all__ = [
    # 日志相关
    "get_logger",
    "LoggerConfig",
    "set_global_log_level",
    "log_with_context",
    "log_error_with_traceback",
    # 设计模式
    "Singleton",
    "LazySingleton",
    "ThreadLocalSingleton",
    # JSON处理
    "safe_json_dumps",
    "safe_json_loads",
    # 时间处理
    "format_time",
    "get_current_timestamp",
    # 错误处理
    "retry_decorator",
    "handle_exception",
    "ErrorContext",
    "safe_execute",
    # 配置工具
    "load_config",
    "save_config",
    # 数据验证
    "validate_input",
    "validate_schema",
    # 缓存相关
    "Cache",
    "LRUCache",
    "MemoryCache",
    "TTLCache",
    "CacheEntry",
    "CacheStats",
    "cache",
    "invalidate_cache",
    # 资源管理
    "ResourceManager",
    "ResourcePool",
    "global_resource_manager",
    # 高级验证器
    "ValidationResult",
    "Validator",
    "NotEmptyValidator",
    "TypeValidator",
    "StringValidator",
    "NumberValidator",
    "ListValidator",
    "DictValidator",
    "DateTimeValidator",
    "EnumValidator",
    "EmailValidator",
    "URLValidator",
    "CustomValidator",
    "CompositeValidator",
    "ValidationSchema",
    "ValidatorRegistry",
    "global_validator_registry",
    # 序列化相关
    "to_json",
    "from_json",
    "to_pickle",
    "from_pickle",
    "to_yaml",
    "from_yaml",
    "serialize",
    "deserialize",
    "register_serializer"
]

# 模块版本
__version__ = '1.0.0'

# 模块描述
__description__ = 'Flora common utilities module providing error handling, logging, caching, resource management, and validation tools.'

# 版本信息
VERSION = (__version__,)

# 导出工具类和函数的别名
error_handler = handle_exception
logger_setup = get_logger
cache_decorator = cache
