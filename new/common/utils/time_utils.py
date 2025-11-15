"""时间工具模块"""
import time
from datetime import datetime, date, timedelta, timezone
from typing import Optional, Union


def get_current_timestamp(ms: bool = False) -> Union[int, float]:
    """
    获取当前时间戳
    
    Args:
        ms: 是否返回毫秒级时间戳
        
    Returns:
        时间戳（秒或毫秒）
    """
    if ms:
        return int(time.time() * 1000)
    return time.time()


def get_current_datetime(tz: Optional[timezone] = None) -> datetime:
    """
    获取当前日期时间
    
    Args:
        tz: 时区，默认为None（本地时区）
        
    Returns:
        当前日期时间对象
    """
    return datetime.now(tz)


def format_time(
    dt: Optional[Union[datetime, date, int, float, str]] = None,
    format_str: str = "%Y-%m-%d %H:%M:%S",
    tz: Optional[timezone] = None
) -> str:
    """
    格式化时间
    
    Args:
        dt: 日期时间对象、时间戳或字符串
        format_str: 格式化字符串
        tz: 时区
        
    Returns:
        格式化后的时间字符串
        
    Raises:
        ValueError: 如果输入格式不正确
    """
    # 如果未提供时间，使用当前时间
    if dt is None:
        dt = get_current_datetime(tz)
    
    # 处理时间戳
    elif isinstance(dt, (int, float)):
        # 检查是否为毫秒级时间戳
        if dt > 1e12:  # 毫秒级时间戳通常大于1e12
            dt = dt / 1000
        dt = datetime.fromtimestamp(dt, tz)
    
    # 处理字符串
    elif isinstance(dt, str):
        try:
            # 尝试解析ISO格式的字符串
            dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
            if tz:
                dt = dt.astimezone(tz)
        except ValueError:
            raise ValueError(f"Cannot parse time string: {dt}")
    
    # 确保是datetime对象
    if isinstance(dt, date) and not isinstance(dt, datetime):
        dt = datetime.combine(dt, datetime.min.time())
    
    # 格式化
    return dt.strftime(format_str)


def parse_time(
    time_str: str,
    format_str: Optional[str] = None,
    tz: Optional[timezone] = None
) -> datetime:
    """
    解析时间字符串
    
    Args:
        time_str: 时间字符串
        format_str: 格式化字符串，如果为None则尝试自动解析
        tz: 时区
        
    Returns:
        解析后的datetime对象
        
    Raises:
        ValueError: 如果解析失败
    """
    if format_str:
        dt = datetime.strptime(time_str, format_str)
        if tz:
            dt = tz.localize(dt)
        return dt
    
    # 尝试ISO格式
    try:
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))
    except ValueError:
        pass
    
    # 尝试几种常见格式
    common_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]
    
    for fmt in common_formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            if tz:
                dt = tz.localize(dt)
            return dt
        except ValueError:
            continue
    
    raise ValueError(f"Cannot parse time string: {time_str}")


def time_diff(
    start: Union[datetime, int, float],
    end: Optional[Union[datetime, int, float]] = None
) -> timedelta:
    """
    计算时间差
    
    Args:
        start: 开始时间
        end: 结束时间，默认为当前时间
        
    Returns:
        时间差
    """
    # 转换为datetime对象
    if isinstance(start, (int, float)):
        start = datetime.fromtimestamp(start)
    
    if end is None:
        end = get_current_datetime()
    elif isinstance(end, (int, float)):
        end = datetime.fromtimestamp(end)
    
    return end - start


def format_duration(td: timedelta) -> str:
    """
    格式化时间差
    
    Args:
        td: 时间差对象
        
    Returns:
        格式化的时间差字符串
    """
    # 计算总秒数
    total_seconds = td.total_seconds()
    
    # 提取各个时间单位
    days = int(total_seconds // 86400)
    hours = int((total_seconds % 86400) // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    
    # 构建结果
    parts = []
    if days > 0:
        parts.append(f"{days}天")
    if hours > 0:
        parts.append(f"{hours}小时")
    if minutes > 0:
        parts.append(f"{minutes}分钟")
    if seconds > 0 or not parts:
        parts.append(f"{seconds}秒")
    
    return " ".join(parts)


def is_valid_time_range(
    start_time: Union[datetime, int, float],
    end_time: Union[datetime, int, float]
) -> bool:
    """
    检查时间范围是否有效
    
    Args:
        start_time: 开始时间
        end_time: 结束时间
        
    Returns:
        是否有效（开始时间早于结束时间）
    """
    # 转换为datetime对象
    if isinstance(start_time, (int, float)):
        start_time = datetime.fromtimestamp(start_time)
    
    if isinstance(end_time, (int, float)):
        end_time = datetime.fromtimestamp(end_time)
    
    return start_time < end_time


def add_time(
    dt: Optional[datetime] = None,
    days: int = 0,
    hours: int = 0,
    minutes: int = 0,
    seconds: int = 0
) -> datetime:
    """
    在指定时间上添加时间间隔
    
    Args:
        dt: 基准时间，默认为当前时间
        days: 天数
        hours: 小时数
        minutes: 分钟数
        seconds: 秒数
        
    Returns:
        计算后的时间
    """
    if dt is None:
        dt = get_current_datetime()
    
    return dt + timedelta(
        days=days,
        hours=hours,
        minutes=minutes,
        seconds=seconds
    )


def get_timezone_offset(tz: Optional[timezone] = None) -> int:
    """
    获取时区偏移（小时）
    
    Args:
        tz: 时区，默认为本地时区
        
    Returns:
        时区偏移（小时）
    """
    if tz is None:
        tz = datetime.now().astimezone().tzinfo
    
    offset = tz.utcoffset(datetime.now())
    if offset:
        return offset.total_seconds() / 3600
    return 0


def timestamp_to_isoformat(timestamp: Union[int, float], ms: bool = False) -> str:
    """
    将时间戳转换为ISO格式字符串
    
    Args:
        timestamp: 时间戳
        ms: 是否为毫秒级时间戳
        
    Returns:
        ISO格式的时间字符串
    """
    if ms:
        timestamp = timestamp / 1000
    return datetime.fromtimestamp(timestamp).isoformat()


def isoformat_to_timestamp(iso_str: str) -> float:
    """
    将ISO格式字符串转换为时间戳
    
    Args:
        iso_str: ISO格式的时间字符串
        
    Returns:
        时间戳（秒）
    """
    dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
    return dt.timestamp()
