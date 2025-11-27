"""JSON工具模块"""
import json
import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Union, TypeVar
from decimal import Decimal
from enum import Enum

from .logger import get_logger

logger = get_logger(__name__)

# 类型定义
JSONSerializable = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


def safe_json_dumps(
    data: Any,
    ensure_ascii: bool = False,
    indent: Optional[int] = None,
    max_depth: int = 20,
    default_handler: Optional[callable] = None
) -> str:
    """
    安全的JSON序列化函数
    处理各种特殊类型，避免序列化错误
    
    Args:
        data: 要序列化的数据
        ensure_ascii: 是否确保ASCII编码
        indent: 缩进空格数，用于美化输出
        max_depth: 最大递归深度
        default_handler: 自定义默认处理函数
        
    Returns:
        序列化后的JSON字符串
        
    Raises:
        Exception: 如果序列化失败
    """
    
    # 深度计数器
    depth_counter = {'value': 0}
    
    def default_encoder(obj: Any) -> Any:
        """
        默认的对象序列化处理函数
        
        Args:
            obj: 需要序列化的对象
            
        Returns:
            可序列化的对象
            
        Raises:
            TypeError: 如果对象无法序列化
        """
        # 检查递归深度
        depth_counter['value'] += 1
        if depth_counter['value'] > max_depth:
            depth_counter['value'] -= 1
            return f"[MAX_DEPTH_REACHED: {type(obj).__name__}]"
        
        try:
            # 处理特殊类型
            if isinstance(obj, (datetime, date)):
                return obj.isoformat()
            
            elif isinstance(obj, Decimal):
                return float(obj)
            
            elif isinstance(obj, Enum):
                return obj.value
            
            elif hasattr(obj, 'to_dict'):
                # 尝试调用对象的to_dict方法
                result = obj.to_dict()
                return result
            
            elif hasattr(obj, '__dict__'):
                # 尝试序列化对象的__dict__属性
                return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}
            
            elif default_handler is not None:
                # 使用自定义处理函数
                return default_handler(obj)
            
            else:
                # 转换为字符串
                return str(obj)
        
        except Exception as e:
            logger.error(f"Failed to serialize object of type {type(obj).__name__}: {str(e)}")
            return f"[UNSERIALIZABLE: {type(obj).__name__}]"
        
        finally:
            depth_counter['value'] -= 1
    
    try:
        return json.dumps(
            data,
            ensure_ascii=ensure_ascii,
            indent=indent,
            default=default_encoder,
            sort_keys=False
        )
    
    except Exception as e:
        logger.error(f"JSON serialization failed: {str(e)}")
        raise


def safe_json_loads(
    json_str: str,
    object_hook: Optional[callable] = None,
    parse_float: Optional[callable] = None,
    parse_int: Optional[callable] = None
) -> JSONSerializable:
    """
    安全的JSON反序列化函数
    处理JSON字符串解析过程中可能出现的错误
    
    Args:
        json_str: JSON字符串
        object_hook: 对象钩子函数
        parse_float: 浮点数解析函数
        parse_int: 整数解析函数
        
    Returns:
        反序列化后的数据结构
        
    Raises:
        ValueError: 如果解析失败
    """
    if not json_str:
        raise ValueError("Empty JSON string")
    
    try:
        return json.loads(
            json_str,
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int
        )
    
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error: {str(e)}")
        raise ValueError(f"Invalid JSON: {str(e)}")
    
    except Exception as e:
        logger.error(f"JSON deserialization failed: {str(e)}")
        raise


def is_json_serializable(obj: Any) -> bool:
    """
    检查对象是否可JSON序列化
    
    Args:
        obj: 要检查的对象
        
    Returns:
        是否可序列化
    """
    try:
        safe_json_dumps(obj)
        return True
    except Exception:
        return False


def json_dumps_compact(data: Any) -> str:
    """
    生成紧凑的JSON字符串
    用于日志记录等场景，减少空间占用
    
    Args:
        data: 要序列化的数据
        
    Returns:
        紧凑的JSON字符串
    """
    return safe_json_dumps(data, ensure_ascii=True, indent=None)


def json_dumps_pretty(data: Any) -> str:
    """
    生成格式化的漂亮JSON字符串
    用于调试和展示
    
    Args:
        data: 要序列化的数据
        
    Returns:
        格式化的JSON字符串
    """
    return safe_json_dumps(data, ensure_ascii=False, indent=2)


def convert_to_json_serializable(obj: Any) -> JSONSerializable:
    """
    将对象转换为可JSON序列化的格式
    递归处理复杂对象结构
    
    Args:
        obj: 要转换的对象
        
    Returns:
        可JSON序列化的数据
    """
    # 基本类型直接返回
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    
    # 处理列表
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    
    # 处理字典
    elif isinstance(obj, dict):
        return {
            convert_to_json_serializable(key): convert_to_json_serializable(value)
            for key, value in obj.items()
            if isinstance(key, (str, int, float, bool))
        }
    
    # 处理日期和时间
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    
    # 处理Decimal
    elif isinstance(obj, Decimal):
        return float(obj)
    
    # 处理枚举
    elif isinstance(obj, Enum):
        return obj.value
    
    # 尝试调用to_dict方法
    elif hasattr(obj, 'to_dict'):
        return convert_to_json_serializable(obj.to_dict())
    
    # 处理对象的__dict__
    elif hasattr(obj, '__dict__'):
        return convert_to_json_serializable({
            k: v for k, v in obj.__dict__.items() if not k.startswith('_')
        })
    
    # 其他类型转换为字符串
    else:
        return str(obj)


def sanitize_json_data(data: Any, max_length: int = 10000) -> str:
    """
    清理JSON数据，确保数据长度合理，避免过大的数据
    
    Args:
        data: 要清理的数据
        max_length: 最大字符串长度
        
    Returns:
        清理后的JSON字符串
    """
    try:
        json_str = safe_json_dumps(data)
        
        # 检查长度
        if len(json_str) > max_length:
            # 截取并添加省略标记
            return json_str[:max_length - 3] + "..."
        
        return json_str
    
    except Exception as e:
        logger.error(f"Failed to sanitize JSON data: {str(e)}")
        return f"[SANITIZATION_FAILED: {str(e)}]"
