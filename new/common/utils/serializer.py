"""
序列化工具模块
提供统一的对象序列化和反序列化接口
"""

import json
import pickle
import yaml
from typing import Any, Dict, Optional, Type
from datetime import datetime
from decimal import Decimal


def to_json(obj: Any, indent: Optional[int] = None, default=None) -> str:
    """
    将对象序列化为JSON字符串
    
    Args:
        obj: 要序列化的对象
        indent: JSON缩进
        default: 自定义默认序列化函数
        
    Returns:
        JSON字符串
    """
    def default_handler(o: Any) -> Any:
        """默认序列化处理函数"""
        if isinstance(o, datetime):
            return o.isoformat()
        elif isinstance(o, Decimal):
            return float(o)
        elif hasattr(o, "to_dict"):
            return o.to_dict()
        elif hasattr(o, "__dict__"):
            return {k: v for k, v in o.__dict__.items() if not k.startswith("_")}
        elif default:
            return default(o)
        else:
            raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")
    
    return json.dumps(obj, indent=indent, default=default_handler, ensure_ascii=False)


def from_json(json_str: str, object_hook=None) -> Any:
    """
    将JSON字符串反序列化为对象
    
    Args:
        json_str: JSON字符串
        object_hook: 自定义反序列化函数
        
    Returns:
        反序列化后的对象
    """
    def object_hook_handler(d: Dict[str, Any]) -> Any:
        """默认反序列化处理函数"""
        if "__class__" in d and "__module__" in d:
            # 尝试反序列化为特定类
            module_name = d["__module__"]
            class_name = d["__class__"]
            try:
                module = __import__(module_name, fromlist=[class_name])
                cls = getattr(module, class_name)
                obj = cls.__new__(cls)  # 创建实例但不调用__init__
                for key, value in d.items():
                    if key not in ["__class__", "__module__"]:
                        setattr(obj, key, value)
                return obj
            except (ImportError, AttributeError):
                return d
        elif "timestamp" in d:
            # 尝试解析时间戳字段
            try:
                d["timestamp"] = datetime.fromisoformat(d["timestamp"])
            except (ValueError, TypeError):
                pass
            return d
        elif object_hook:
            return object_hook(d)
        else:
            return d
    
    return json.loads(json_str, object_hook=object_hook_handler)


def to_pickle(obj: Any) -> bytes:
    """
    将对象序列化为pickle字节
    
    Args:
        obj: 要序列化的对象
        
    Returns:
        pickle字节
    """
    return pickle.dumps(obj, protocol=pickle.HIGHEST_PROTOCOL)


def from_pickle(pickle_data: bytes) -> Any:
    """
    将pickle字节反序列化为对象
    
    Args:
        pickle_data: pickle字节
        
    Returns:
        反序列化后的对象
    """
    return pickle.loads(pickle_data)


def to_yaml(obj: Any) -> str:
    """
    将对象序列化为YAML字符串
    
    Args:
        obj: 要序列化的对象
        
    Returns:
        YAML字符串
    """
    class CustomDumper(yaml.Dumper):
        """自定义YAML Dumper类，处理特殊类型"""
        def represent_datetime(self, data):
            return self.represent_scalar('tag:yaml.org,2002:timestamp', data.isoformat())
        
        def represent_decimal(self, data):
            return self.represent_float(float(data))
        
        def represent_object(self, data):
            if hasattr(data, 'to_dict'):
                return self.represent_dict(data.to_dict())
            elif hasattr(data, '__dict__'):
                # 过滤掉私有属性
                obj_dict = {k: v for k, v in data.__dict__.items() if not k.startswith('_')}
                return self.represent_dict(obj_dict)
            else:
                # 回退到默认表示
                return super().represent_undefined(data)
    
    # 注册自定义类型处理
    CustomDumper.add_representer(datetime, CustomDumper.represent_datetime)
    CustomDumper.add_representer(Decimal, CustomDumper.represent_decimal)
    
    # 注册默认处理函数（需放在类型处理之后）
    CustomDumper.add_multi_representer(object, CustomDumper.represent_object)
    
    return yaml.dump(obj, default_flow_style=False, default_style=None, allow_unicode=True, Dumper=CustomDumper)


def from_yaml(yaml_str: str) -> Any:
    """
    将YAML字符串反序列化为对象
    
    Args:
        yaml_str: YAML字符串
        
    Returns:
        反序列化后的对象
    """
    def construct_datetime(loader, node):
        """YAML时间戳构造函数"""
        return datetime.fromisoformat(node.value)
    
    loader = yaml.SafeLoader
    loader.add_constructor('tag:yaml.org,2002:timestamp', construct_datetime)
    
    return yaml.load(yaml_str, Loader=loader)


def serialize(obj: Any, format: str = "json", **kwargs) -> str:
    """
    统一序列化接口
    
    Args:
        obj: 要序列化的对象
        format: 序列化格式（json, yaml, pickle）
        **kwargs: 额外参数
        
    Returns:
        序列化后的字符串或字节
    """
    format = format.lower()
    
    if format == "json":
        return to_json(obj, **kwargs)
    elif format == "yaml":
        return to_yaml(obj, **kwargs)
    elif format == "pickle":
        return to_pickle(obj)
    else:
        raise ValueError(f"Unsupported serialization format: {format}")


def deserialize(data: Any, format: str = "json", **kwargs) -> Any:
    """
    统一反序列化接口
    
    Args:
        data: 要反序列化的数据
        format: 序列化格式（json, yaml, pickle）
        **kwargs: 额外参数
        
    Returns:
        反序列化后的对象
    """
    format = format.lower()
    
    if format == "json":
        return from_json(data, **kwargs)
    elif format == "yaml":
        return from_yaml(data, **kwargs)
    elif format == "pickle":
        return from_pickle(data)
    else:
        raise ValueError(f"Unsupported deserialization format: {format}")


def register_serializer(format: str, serializer_func, deserializer_func) -> None:
    """
    注册自定义序列化器
    
    Args:
        format: 序列化格式名称
        serializer_func: 序列化函数
        deserializer_func: 反序列化函数
        
    Returns:
        None
    """
    global _serializers
    _serializers[format.lower()] = (serializer_func, deserializer_func)


# 初始化自定义序列化器映射
_serializers = {
    "json": (to_json, from_json),
    "yaml": (to_yaml, from_yaml),
    "pickle": (to_pickle, from_pickle)
}
