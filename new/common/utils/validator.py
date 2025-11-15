"""数据验证工具模块"""
import re
import json
import logging
import datetime
from typing import Any, Callable, Dict, List, Optional, Pattern, Set, Tuple, TypeVar, Union, Generic, cast
from collections import defaultdict

from .logger import get_logger
from .error_handling import ValidationError, ErrorContext

logger = get_logger(__name__)

T = TypeVar('T')


class ValidationResult:
    """验证结果类"""
    
    def __init__(self, is_valid: bool, errors: Optional[Dict[str, List[str]]] = None):
        """
        初始化验证结果
        
        Args:
            is_valid: 是否验证通过
            errors: 错误信息，格式为 {field_path: [error_messages]}
        """
        self.is_valid = is_valid
        self.errors = errors or {}
    
    def __bool__(self) -> bool:
        """布尔值转换，验证通过返回True"""
        return self.is_valid
    
    def __repr__(self) -> str:
        """字符串表示"""
        if self.is_valid:
            return "ValidationResult(valid=True)"
        return f"ValidationResult(valid=False, errors={self.errors})"
    
    def add_error(self, field_path: str, error_message: str) -> None:
        """
        添加错误信息
        
        Args:
            field_path: 字段路径
            error_message: 错误信息
        """
        if field_path not in self.errors:
            self.errors[field_path] = []
        self.errors[field_path].append(error_message)
        self.is_valid = False
    
    def merge(self, other: 'ValidationResult') -> 'ValidationResult':
        """
        合并两个验证结果
        
        Args:
            other: 另一个验证结果
            
        Returns:
            合并后的验证结果
        """
        merged_errors = defaultdict(list)
        
        # 合并当前错误
        for field, messages in self.errors.items():
            merged_errors[field].extend(messages)
        
        # 合并其他错误
        for field, messages in other.errors.items():
            merged_errors[field].extend(messages)
        
        return ValidationResult(self.is_valid and other.is_valid, dict(merged_errors))


class Validator:
    """验证器基类"""
    
    def validate(self, value: Any) -> ValidationResult:
        """
        验证值
        
        Args:
            value: 要验证的值
            
        Returns:
            验证结果
        """
        raise NotImplementedError("validate method must be implemented")


class NotEmptyValidator(Validator):
    """非空验证器"""
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        if value is None:
            result.add_error("value", "Value cannot be None")
        elif isinstance(value, str) and not value.strip():
            result.add_error("value", "String cannot be empty")
        elif isinstance(value, (list, tuple, set, dict)) and len(value) == 0:
            result.add_error("value", f"{type(value).__name__} cannot be empty")
        
        return result


class TypeValidator(Validator):
    """类型验证器"""
    
    def __init__(self, expected_type: Union[type, Tuple[type, ...]]):
        """
        初始化类型验证器
        
        Args:
            expected_type: 期望的类型或类型元组
        """
        self.expected_type = expected_type
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        if value is not None and not isinstance(value, self.expected_type):
            result.add_error("value", f"Expected type {self.expected_type}, got {type(value).__name__}")
        
        return result


class StringValidator(Validator):
    """字符串验证器"""
    
    def __init__(self,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 pattern: Optional[Union[str, Pattern]] = None,
                 allow_empty: bool = False):
        """
        初始化字符串验证器
        
        Args:
            min_length: 最小长度
            max_length: 最大长度
            pattern: 正则表达式模式
            allow_empty: 是否允许空字符串
        """
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern if isinstance(pattern, Pattern) else (re.compile(pattern) if pattern else None)
        self.allow_empty = allow_empty
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        # 首先验证类型
        if not isinstance(value, str):
            result.add_error("value", f"Expected string type, got {type(value).__name__}")
            return result
        
        # 验证空值
        if not self.allow_empty and not value.strip():
            result.add_error("value", "String cannot be empty")
        
        # 验证长度
        length = len(value)
        if self.min_length is not None and length < self.min_length:
            result.add_error("value", f"String length must be at least {self.min_length}")
        
        if self.max_length is not None and length > self.max_length:
            result.add_error("value", f"String length must be at most {self.max_length}")
        
        # 验证正则表达式
        if self.pattern and not self.pattern.match(value):
            result.add_error("value", f"String does not match pattern {self.pattern.pattern}")
        
        return result


class NumberValidator(Validator):
    """数字验证器"""
    
    def __init__(self,
                 min_value: Optional[Union[int, float]] = None,
                 max_value: Optional[Union[int, float]] = None,
                 is_integer: bool = False):
        """
        初始化数字验证器
        
        Args:
            min_value: 最小值
            max_value: 最大值
            is_integer: 是否必须为整数
        """
        self.min_value = min_value
        self.max_value = max_value
        self.is_integer = is_integer
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        # 验证类型
        if not isinstance(value, (int, float)):
            result.add_error("value", f"Expected number type, got {type(value).__name__}")
            return result
        
        # 验证整数
        if self.is_integer and not isinstance(value, int):
            result.add_error("value", "Number must be an integer")
        
        # 验证范围
        if self.min_value is not None and value < self.min_value:
            result.add_error("value", f"Number must be at least {self.min_value}")
        
        if self.max_value is not None and value > self.max_value:
            result.add_error("value", f"Number must be at most {self.max_value}")
        
        return result


class ListValidator(Validator):
    """列表验证器"""
    
    def __init__(self,
                 min_length: Optional[int] = None,
                 max_length: Optional[int] = None,
                 item_validator: Optional[Validator] = None,
                 allow_empty: bool = True):
        """
        初始化列表验证器
        
        Args:
            min_length: 最小长度
            max_length: 最大长度
            item_validator: 列表项验证器
            allow_empty: 是否允许空列表
        """
        self.min_length = min_length
        self.max_length = max_length
        self.item_validator = item_validator
        self.allow_empty = allow_empty
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        # 验证类型
        if not isinstance(value, (list, tuple)):
            result.add_error("value", f"Expected list or tuple type, got {type(value).__name__}")
            return result
        
        # 验证空列表
        if not self.allow_empty and len(value) == 0:
            result.add_error("value", "List cannot be empty")
        
        # 验证长度
        length = len(value)
        if self.min_length is not None and length < self.min_length:
            result.add_error("value", f"List length must be at least {self.min_length}")
        
        if self.max_length is not None and length > self.max_length:
            result.add_error("value", f"List length must be at most {self.max_length}")
        
        # 验证列表项
        if self.item_validator:
            for index, item in enumerate(value):
                item_result = self.item_validator.validate(item)
                if not item_result.is_valid:
                    # 为每个错误添加索引前缀
                    for field_path, messages in item_result.errors.items():
                        new_field_path = f"[{index}].{field_path}"
                        for message in messages:
                            result.add_error(new_field_path, message)
        
        return result


class DictValidator(Validator):
    """字典验证器"""
    
    def __init__(self,
                 schema: Optional[Dict[str, Validator]] = None,
                 required_fields: Optional[Set[str]] = None,
                 allow_extra_fields: bool = True):
        """
        初始化字典验证器
        
        Args:
            schema: 字段验证器映射
            required_fields: 必填字段集合
            allow_extra_fields: 是否允许额外字段
        """
        self.schema = schema or {}
        self.required_fields = required_fields or set()
        self.allow_extra_fields = allow_extra_fields
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        # 验证类型
        if not isinstance(value, dict):
            result.add_error("value", f"Expected dict type, got {type(value).__name__}")
            return result
        
        # 验证必填字段
        for field in self.required_fields:
            if field not in value:
                result.add_error(field, f"Field '{field}' is required")
        
        # 验证schema中的字段
        for field, validator in self.schema.items():
            if field in value:
                field_result = validator.validate(value[field])
                if not field_result.is_valid:
                    # 为每个错误添加字段名前缀
                    for field_path, messages in field_result.errors.items():
                        new_field_path = f"{field}.{field_path}" if field_path != "value" else field
                        for message in messages:
                            result.add_error(new_field_path, message)
        
        # 验证额外字段
        if not self.allow_extra_fields:
            extra_fields = set(value.keys()) - set(self.schema.keys()) - self.required_fields
            for field in extra_fields:
                result.add_error(field, f"Extra field '{field}' not allowed")
        
        return result


class DateTimeValidator(Validator):
    """日期时间验证器"""
    
    def __init__(self,
                 min_datetime: Optional[datetime.datetime] = None,
                 max_datetime: Optional[datetime.datetime] = None,
                 format_str: Optional[str] = None):
        """
        初始化日期时间验证器
        
        Args:
            min_datetime: 最小日期时间
            max_datetime: 最大日期时间
            format_str: 日期时间格式字符串，如果提供则用于解析字符串值
        """
        self.min_datetime = min_datetime
        self.max_datetime = max_datetime
        self.format_str = format_str
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        # 处理字符串值
        if isinstance(value, str) and self.format_str:
            try:
                value = datetime.datetime.strptime(value, self.format_str)
            except ValueError:
                result.add_error("value", f"Invalid datetime format, expected {self.format_str}")
                return result
        
        # 验证类型
        if not isinstance(value, datetime.datetime):
            result.add_error("value", f"Expected datetime type, got {type(value).__name__}")
            return result
        
        # 验证范围
        if self.min_datetime is not None and value < self.min_datetime:
            result.add_error("value", f"Datetime must be after {self.min_datetime}")
        
        if self.max_datetime is not None and value > self.max_datetime:
            result.add_error("value", f"Datetime must be before {self.max_datetime}")
        
        return result


class EnumValidator(Validator):
    """枚举验证器"""
    
    def __init__(self, enum_values: Union[List[Any], Set[Any], Tuple[Any, ...]]):
        """
        初始化枚举验证器
        
        Args:
            enum_values: 允许的值集合
        """
        self.enum_values = set(enum_values)
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        if value not in self.enum_values:
            result.add_error("value", f"Value must be one of {list(self.enum_values)}")
        
        return result


class EmailValidator(Validator):
    """邮箱验证器"""
    
    def __init__(self):
        """初始化邮箱验证器"""
        # 简单的邮箱正则表达式
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        # 验证类型
        if not isinstance(value, str):
            result.add_error("value", f"Expected string type, got {type(value).__name__}")
            return result
        
        # 验证邮箱格式
        if not self.email_pattern.match(value):
            result.add_error("value", "Invalid email format")
        
        return result


class URLValidator(Validator):
    """URL验证器"""
    
    def __init__(self):
        """初始化URL验证器"""
        # 简单的URL正则表达式
        self.url_pattern = re.compile(r'^https?://(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$')
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        # 验证类型
        if not isinstance(value, str):
            result.add_error("value", f"Expected string type, got {type(value).__name__}")
            return result
        
        # 验证URL格式
        if not self.url_pattern.match(value):
            result.add_error("value", "Invalid URL format")
        
        return result


class CustomValidator(Validator):
    """自定义验证器"""
    
    def __init__(self, validate_func: Callable[[Any], ValidationResult]):
        """
        初始化自定义验证器
        
        Args:
            validate_func: 验证函数，接受值并返回ValidationResult
        """
        self.validate_func = validate_func
    
    def validate(self, value: Any) -> ValidationResult:
        try:
            return self.validate_func(value)
        except Exception as e:
            logger.error(f"Custom validator error: {str(e)}")
            result = ValidationResult(False)
            result.add_error("value", f"Validation error: {str(e)}")
            return result


class CompositeValidator(Validator):
    """复合验证器"""
    
    def __init__(self, validators: List[Validator]):
        """
        初始化复合验证器
        
        Args:
            validators: 验证器列表
        """
        self.validators = validators
    
    def validate(self, value: Any) -> ValidationResult:
        result = ValidationResult(True)
        
        for validator in self.validators:
            validator_result = validator.validate(value)
            result = result.merge(validator_result)
        
        return result


class ValidationSchema:
    """验证模式"""
    
    def __init__(self):
        """初始化验证模式"""
        self.validators: Dict[str, Validator] = {}
    
    def add_field(self, field_name: str, validator: Validator) -> 'ValidationSchema':
        """
        添加字段验证器
        
        Args:
            field_name: 字段名
            validator: 验证器
            
        Returns:
            验证模式自身，用于链式调用
        """
        self.validators[field_name] = validator
        return self
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """
        验证数据
        
        Args:
            data: 要验证的数据
            
        Returns:
            验证结果
        """
        result = ValidationResult(True)
        
        if not isinstance(data, dict):
            result.add_error("data", "Expected dictionary data")
            return result
        
        for field_name, validator in self.validators.items():
            if field_name in data:
                field_result = validator.validate(data[field_name])
                if not field_result.is_valid:
                    # 为每个错误添加字段名前缀
                    for field_path, messages in field_result.errors.items():
                        new_field_path = f"{field_name}.{field_path}" if field_path != "value" else field_name
                        for message in messages:
                            result.add_error(new_field_path, message)
        
        return result


class ValidatorRegistry:
    """验证器注册表"""
    
    def __init__(self):
        """初始化验证器注册表"""
        self.validators: Dict[str, Validator] = {}
    
    def register(self, name: str, validator: Validator) -> None:
        """
        注册验证器
        
        Args:
            name: 验证器名称
            validator: 验证器实例
        """
        self.validators[name] = validator
        logger.info(f"Registered validator: {name}")
    
    def get(self, name: str) -> Optional[Validator]:
        """
        获取验证器
        
        Args:
            name: 验证器名称
            
        Returns:
            验证器实例或None
        """
        return self.validators.get(name)
    
    def unregister(self, name: str) -> None:
        """
        注销验证器
        
        Args:
            name: 验证器名称
        """
        if name in self.validators:
            del self.validators[name]
            logger.info(f"Unregistered validator: {name}")


# 创建全局验证器注册表实例
global_validator_registry = ValidatorRegistry()