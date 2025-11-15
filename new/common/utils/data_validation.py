"""数据验证工具模块"""
import re
import logging
from typing import Any, Dict, List, Optional, Union, Callable

from .logger import get_logger

logger = get_logger(__name__)

# 常见的验证模式
VALIDATION_PATTERNS = {
    'email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
    'phone': r'^\+?[1-9]\d{1,14}$',  # E.164 格式
    'url': r'^https?://[\w\-]+(\.[\w\-]+)+([\w\-.,@?^=%&:/~+#]*[\w\-@?^=%&/~+#])?$',
    'ipv4': r'^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$',
    'ipv6': r'^(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0-9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}:){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9]))$',
    'uuid': r'^[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}$',
    'alphanumeric': r'^[a-zA-Z0-9]+$',
    'hex_color': r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
}


def validate_input(
    value: Any,
    expected_type: Optional[type] = None,
    min_length: Optional[int] = None,
    max_length: Optional[int] = None,
    min_value: Optional[Union[int, float]] = None,
    max_value: Optional[Union[int, float]] = None,
    regex_pattern: Optional[str] = None,
    in_list: Optional[List[Any]] = None,
    not_null: bool = True,
    custom_validator: Optional[Callable[[Any], bool]] = None,
    error_message: Optional[str] = None
) -> tuple[bool, str]:
    """
    验证输入值
    
    Args:
        value: 要验证的值
        expected_type: 期望的数据类型
        min_length: 最小长度（适用于字符串、列表等）
        max_length: 最大长度（适用于字符串、列表等）
        min_value: 最小值（适用于数字）
        max_value: 最大值（适用于数字）
        regex_pattern: 正则表达式模式
        in_list: 允许的值列表
        not_null: 是否不允许为None
        custom_validator: 自定义验证函数
        error_message: 自定义错误消息
        
    Returns:
        (是否有效, 错误消息)
    """
    # 检查是否为None
    if value is None:
        if not_null:
            return False, error_message or "Value cannot be None"
        return True, ""
    
    # 检查数据类型
    if expected_type and not isinstance(value, expected_type):
        return False, error_message or f"Expected type {expected_type.__name__}, got {type(value).__name__}"
    
    # 检查长度
    if hasattr(value, '__len__'):
        if min_length is not None and len(value) < min_length:
            return False, error_message or f"Length must be at least {min_length}"
        if max_length is not None and len(value) > max_length:
            return False, error_message or f"Length must be at most {max_length}"
    
    # 检查数值范围
    if isinstance(value, (int, float)):
        if min_value is not None and value < min_value:
            return False, error_message or f"Value must be at least {min_value}"
        if max_value is not None and value > max_value:
            return False, error_message or f"Value must be at most {max_value}"
    
    # 正则表达式验证
    if regex_pattern and isinstance(value, str):
        # 支持预定义的模式名称
        if regex_pattern in VALIDATION_PATTERNS:
            pattern = VALIDATION_PATTERNS[regex_pattern]
        else:
            pattern = regex_pattern
        
        if not re.match(pattern, value):
            return False, error_message or f"Value does not match pattern {regex_pattern}"
    
    # 检查是否在允许的列表中
    if in_list is not None:
        if value not in in_list:
            return False, error_message or f"Value must be one of {in_list}"
    
    # 自定义验证函数
    if custom_validator:
        try:
            if not custom_validator(value):
                return False, error_message or "Custom validation failed"
        except Exception as e:
            logger.error(f"Custom validator error: {str(e)}")
            return False, error_message or f"Custom validator error: {str(e)}"
    
    return True, ""


def validate_schema(
    data: Dict[str, Any],
    schema: Dict[str, Dict[str, Any]],
    allow_extra_keys: bool = True
) -> tuple[bool, Dict[str, str]]:
    """
    根据schema验证数据字典
    
    Args:
        data: 要验证的数据字典
        schema: schema定义，格式为 {field_name: {validation_rules}}
        allow_extra_keys: 是否允许额外的键
        
    Returns:
        (是否有效, 错误消息字典)
    """
    errors: Dict[str, str] = {}
    
    # 验证schema中定义的字段
    for field_name, rules in schema.items():
        value = data.get(field_name)
        
        # 检查是否必需
        if rules.get('required', False) and field_name not in data:
            errors[field_name] = "This field is required"
            continue
        
        # 如果字段存在，进行验证
        if field_name in data:
            # 提取验证规则
            validation_rules = rules.copy()
            # 移除特殊规则
            validation_rules.pop('required', None)
            validation_rules.pop('description', None)
            
            # 执行验证
            is_valid, error = validate_input(value, **validation_rules)
            if not is_valid:
                errors[field_name] = error
    
    # 检查是否有额外的键
    if not allow_extra_keys:
        schema_fields = set(schema.keys())
        data_fields = set(data.keys())
        extra_fields = data_fields - schema_fields
        
        for field in extra_fields:
            errors[field] = "Unexpected field"
    
    return len(errors) == 0, errors


def sanitize_string(
    value: str,
    strip_whitespace: bool = True,
    max_length: Optional[int] = None,
    allowed_chars: Optional[str] = None
) -> str:
    """
    清理字符串输入
    
    Args:
        value: 输入字符串
        strip_whitespace: 是否去除首尾空白
        max_length: 最大长度
        allowed_chars: 允许的字符集（正则表达式字符类）
        
    Returns:
        清理后的字符串
    """
    if not isinstance(value, str):
        value = str(value)
    
    # 去除首尾空白
    if strip_whitespace:
        value = value.strip()
    
    # 限制长度
    if max_length is not None and len(value) > max_length:
        value = value[:max_length]
    
    # 过滤字符
    if allowed_chars:
        # 创建正则表达式模式
        pattern = f"[^({allowed_chars})]"
        value = re.sub(pattern, '', value)
    
    return value


def validate_email(email: str) -> bool:
    """
    验证电子邮件地址
    
    Args:
        email: 电子邮件地址
        
    Returns:
        是否有效
    """
    pattern = VALIDATION_PATTERNS['email']
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """
    验证URL
    
    Args:
        url: URL字符串
        
    Returns:
        是否有效
    """
    pattern = VALIDATION_PATTERNS['url']
    return bool(re.match(pattern, url))


def validate_phone(phone: str) -> bool:
    """
    验证电话号码（E.164格式）
    
    Args:
        phone: 电话号码
        
    Returns:
        是否有效
    """
    pattern = VALIDATION_PATTERNS['phone']
    return bool(re.match(pattern, phone))


def validate_uuid(uuid: str) -> bool:
    """
    验证UUID
    
    Args:
        uuid: UUID字符串
        
    Returns:
        是否有效
    """
    pattern = VALIDATION_PATTERNS['uuid']
    return bool(re.match(pattern, uuid))


def validate_ip(ip: str) -> bool:
    """
    验证IP地址（IPv4或IPv6）
    
    Args:
        ip: IP地址字符串
        
    Returns:
        是否有效
    """
    return validate_ipv4(ip) or validate_ipv6(ip)


def validate_ipv4(ip: str) -> bool:
    """
    验证IPv4地址
    
    Args:
        ip: IPv4地址字符串
        
    Returns:
        是否有效
    """
    pattern = VALIDATION_PATTERNS['ipv4']
    return bool(re.match(pattern, ip))


def validate_ipv6(ip: str) -> bool:
    """
    验证IPv6地址
    
    Args:
        ip: IPv6地址字符串
        
    Returns:
        是否有效
    """
    pattern = VALIDATION_PATTERNS['ipv6']
    return bool(re.match(pattern, ip))


def validate_alphanumeric(text: str) -> bool:
    """
    验证是否仅包含字母和数字
    
    Args:
        text: 输入文本
        
    Returns:
        是否有效
    """
    pattern = VALIDATION_PATTERNS['alphanumeric']
    return bool(re.match(pattern, text))


def validate_password(
    password: str,
    min_length: int = 8,
    require_uppercase: bool = True,
    require_lowercase: bool = True,
    require_digit: bool = True,
    require_special: bool = False
) -> tuple[bool, List[str]]:
    """
    验证密码强度
    
    Args:
        password: 密码字符串
        min_length: 最小长度
        require_uppercase: 是否需要大写字母
        require_lowercase: 是否需要小写字母
        require_digit: 是否需要数字
        require_special: 是否需要特殊字符
        
    Returns:
        (是否有效, 错误消息列表)
    """
    errors: List[str] = []
    
    # 检查长度
    if len(password) < min_length:
        errors.append(f"Password must be at least {min_length} characters long")
    
    # 检查大写字母
    if require_uppercase and not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    # 检查小写字母
    if require_lowercase and not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    # 检查数字
    if require_digit and not re.search(r'[0-9]', password):
        errors.append("Password must contain at least one digit")
    
    # 检查特殊字符
    if require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        errors.append("Password must contain at least one special character")
    
    return len(errors) == 0, errors