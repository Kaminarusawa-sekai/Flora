"""日志工具模块"""
import logging
import os
import sys
from datetime import datetime
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler


class LoggerConfig:
    """
    日志配置类
    用于统一管理和配置系统日志
    """
    
    # 默认日志级别
    DEFAULT_LOG_LEVEL = logging.INFO
    
    # 默认日志格式
    DEFAULT_LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # 默认日期格式
    DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # 默认日志文件大小（50MB）
    DEFAULT_MAX_BYTES = 50 * 1024 * 1024
    
    # 默认备份数量
    DEFAULT_BACKUP_COUNT = 3
    
    def __init__(
        self,
        log_level: int = DEFAULT_LOG_LEVEL,
        log_format: str = DEFAULT_LOG_FORMAT,
        date_format: str = DEFAULT_DATE_FORMAT,
        log_file: Optional[str] = None,
        use_rotating_file: bool = False,
        use_timed_rotating: bool = False,
        max_bytes: int = DEFAULT_MAX_BYTES,
        backup_count: int = DEFAULT_BACKUP_COUNT,
        when: str = 'midnight',
        interval: int = 1,
        console_log: bool = True
    ):
        """
        初始化日志配置
        
        Args:
            log_level: 日志级别
            log_format: 日志格式
            date_format: 日期格式
            log_file: 日志文件路径
            use_rotating_file: 是否使用按大小轮转的文件处理器
            use_timed_rotating: 是否使用按时间轮转的文件处理器
            max_bytes: 单个日志文件最大字节数（仅用于RotatingFileHandler）
            backup_count: 备份文件数量
            when: 时间轮转的时间单位（仅用于TimedRotatingFileHandler）
            interval: 轮转间隔（仅用于TimedRotatingFileHandler）
            console_log: 是否输出到控制台
        """
        self.log_level = log_level
        self.log_format = log_format
        self.date_format = date_format
        self.log_file = log_file
        self.use_rotating_file = use_rotating_file
        self.use_timed_rotating = use_timed_rotating
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.when = when
        self.interval = interval
        self.console_log = console_log


# 全局日志配置实例
DEFAULT_CONFIG = LoggerConfig()

# 已创建的logger字典，用于避免重复创建
global_loggers: Dict[str, logging.Logger] = {}


def get_logger(
    name: str = __name__,
    config: Optional[LoggerConfig] = None
) -> logging.Logger:
    """
    获取或创建一个logger实例
    
    Args:
        name: logger名称，通常使用__name__
        config: 日志配置，如果为None则使用默认配置
        
    Returns:
        配置好的logger实例
    """
    # 检查是否已经创建过该logger
    if name in global_loggers:
        return global_loggers[name]
    
    # 使用默认配置或自定义配置
    current_config = config or DEFAULT_CONFIG
    
    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(current_config.log_level)
    logger.propagate = False  # 防止日志重复输出
    
    # 创建formatter
    formatter = logging.Formatter(
        fmt=current_config.log_format,
        datefmt=current_config.date_format
    )
    
    # 添加控制台处理器
    if current_config.console_log:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(current_config.log_level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    # 添加文件处理器
    if current_config.log_file:
        # 确保日志目录存在
        log_dir = os.path.dirname(current_config.log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        # 根据配置选择不同的文件处理器
        if current_config.use_rotating_file:
            file_handler = RotatingFileHandler(
                filename=current_config.log_file,
                maxBytes=current_config.max_bytes,
                backupCount=current_config.backup_count,
                encoding='utf-8'
            )
        elif current_config.use_timed_rotating:
            file_handler = TimedRotatingFileHandler(
                filename=current_config.log_file,
                when=current_config.when,
                interval=current_config.interval,
                backupCount=current_config.backup_count,
                encoding='utf-8'
            )
        else:
            file_handler = logging.FileHandler(
                filename=current_config.log_file,
                encoding='utf-8'
            )
        
        file_handler.setLevel(current_config.log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # 保存到全局字典中
    global_loggers[name] = logger
    
    return logger


def set_global_log_level(level: int) -> None:
    """
    设置全局默认日志级别
    
    Args:
        level: 日志级别
    """
    global DEFAULT_CONFIG
    DEFAULT_CONFIG.log_level = level
    
    # 更新已存在的所有logger
    for logger in global_loggers.values():
        logger.setLevel(level)
        for handler in logger.handlers:
            handler.setLevel(level)


def log_with_context(logger: logging.Logger, level: int, message: str, **context) -> None:
    """
    记录带有上下文信息的日志
    
    Args:
        logger: logger实例
        level: 日志级别
        message: 日志消息
        **context: 上下文信息，将作为额外信息添加到日志中
    """
    context_str = ', '.join([f"{k}={v}" for k, v in context.items()])
    full_message = f"{message} [context: {context_str}]"
    logger.log(level, full_message)


def log_error_with_traceback(logger: logging.Logger, error: Exception, message: str = "Error occurred") -> None:
    """
    记录带有完整堆栈跟踪的错误日志
    
    Args:
        logger: logger实例
        error: 异常对象
        message: 错误消息前缀
    """
    logger.error(f"{message}: {str(error)}", exc_info=True)
