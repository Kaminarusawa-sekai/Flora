"""错误处理工具模块"""
import logging
import traceback
import time
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar, Union

from .logger import get_logger
from .time_utils import get_current_timestamp

logger = get_logger(__name__)


class ValidationError(Exception):
    """
    验证错误异常
    用于数据验证失败时抛出
    """
    def __init__(self, message: str = "Validation failed", field: Optional[str] = None, value: Optional[Any] = None):
        self.message = message
        self.field = field
        self.value = value
        super().__init__(self.message)

    def __str__(self):
        if self.field:
            return f"{self.message}: Field '{self.field}' with value '{self.value}'"
        return self.message

# 类型定义
T = TypeVar('T')
ErrorType = Union[Type[Exception], tuple[Type[Exception], ...]]


def retry_decorator(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: ErrorType = Exception,
    log_errors: bool = True,
    log_level: int = logging.ERROR,
    fail_silently: bool = False,
    default_return: Any = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    重试装饰器
    在指定的异常发生时自动重试函数调用
    
    Args:
        max_retries: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避因子，每次重试的延迟会乘以这个因子
        exceptions: 要捕获的异常类型
        log_errors: 是否记录错误日志
        log_level: 日志级别
        fail_silently: 是否静默失败（返回默认值而不是抛出异常）
        default_return: 失败时的默认返回值
        
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):  # +1 for the initial attempt
                try:
                    # 记录尝试开始
                    if log_errors and attempt > 0:
                        logger.log(
                            logging.INFO,
                            f"Retrying {func.__name__} (attempt {attempt}/{max_retries})..."
                        )
                    
                    # 执行原始函数
                    return func(*args, **kwargs)
                
                except exceptions as e:
                    last_exception = e
                    
                    # 记录错误
                    if log_errors:
                        error_info = {
                            'function': func.__name__,
                            'attempt': attempt,
                            'max_retries': max_retries,
                            'error': str(e),
                            'traceback': traceback.format_exc()
                        }
                        
                        logger.log(
                            log_level,
                            f"Error in {func.__name__} (attempt {attempt}/{max_retries}): {str(e)}",
                            extra=error_info
                        )
                    
                    # 检查是否还有重试机会
                    if attempt < max_retries:
                        # 计算下一次的延迟时间
                        sleep_time = current_delay * (backoff ** attempt)
                        
                        if log_errors:
                            logger.log(
                                logging.INFO,
                                f"Will retry {func.__name__} after {sleep_time:.2f} seconds..."
                            )
                        
                        # 等待
                        time.sleep(sleep_time)
                    else:
                        # 达到最大重试次数
                        if fail_silently:
                            logger.log(
                                log_level,
                                f"Failed after {max_retries} retries. Returning default value."
                            )
                            return default_return
                        else:
                            raise
            
            # 理论上不应该到达这里，但为了类型安全添加
            raise RuntimeError("Unexpected flow in retry_decorator")
        
        return wrapper
    
    return decorator


def handle_exception(
    func: Optional[Callable[..., T]] = None,
    catch: ErrorType = Exception,
    default_return: Any = None,
    log_error: bool = True,
    log_level: int = logging.ERROR,
    re_raise: bool = False,
    error_handler: Optional[Callable[[Exception], Any]] = None
) -> Union[Callable[[Callable[..., T]], Callable[..., T]], Callable[..., T]]:
    """
    异常处理装饰器
    捕获指定类型的异常并进行处理
    
    Args:
        func: 要装饰的函数
        catch: 要捕获的异常类型
        default_return: 默认返回值
        log_error: 是否记录错误
        log_level: 日志级别
        re_raise: 是否重新抛出异常
        error_handler: 自定义错误处理函数
        
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            try:
                return func(*args, **kwargs)
            
            except catch as e:
                # 记录错误
                if log_error:
                    error_info = {
                        'function': func.__name__,
                        'error': str(e),
                        'traceback': traceback.format_exc()
                    }
                    logger.log(
                        log_level,
                        f"Exception in {func.__name__}: {str(e)}",
                        extra=error_info
                    )
                
                # 自定义错误处理
                if error_handler is not None:
                    try:
                        result = error_handler(e)
                        if re_raise:
                            raise
                        return result
                    except Exception:
                        # 如果错误处理函数抛出异常，继续原来的处理流程
                        pass
                
                # 重新抛出异常
                if re_raise:
                    raise
                
                # 返回默认值
                return default_return
        
        return wrapper
    
    # 支持不带参数的调用方式
    if func is None:
        return decorator
    
    return decorator(func)


class ErrorContext:
    """
    错误上下文管理器
    用于在特定上下文中捕获和处理异常
    """
    
    def __init__(
        self,
        catch: ErrorType = Exception,
        context_name: str = "unknown",
        log_error: bool = True,
        log_level: int = logging.ERROR,
        re_raise: bool = False,
        on_error: Optional[Callable[[Exception], Any]] = None
    ):
        """
        初始化错误上下文管理器
        
        Args:
            catch: 要捕获的异常类型
            context_name: 上下文名称
            log_error: 是否记录错误
            log_level: 日志级别
            re_raise: 是否重新抛出异常
            on_error: 错误回调函数
        """
        self.catch = catch
        self.context_name = context_name
        self.log_error = log_error
        self.log_level = log_level
        self.re_raise = re_raise
        self.on_error = on_error
        self.exception = None
    
    def __enter__(self) -> 'ErrorContext':
        """进入上下文"""
        return self
    
    def __exit__(self, exc_type: Type[Exception], exc_val: Exception, exc_tb) -> bool:
        """
        退出上下文
        
        Returns:
            是否抑制异常
        """
        if exc_type is not None and issubclass(exc_type, self.catch):
            self.exception = exc_val
            
            # 记录错误
            if self.log_error:
                error_info = {
                    'context': self.context_name,
                    'error': str(exc_val),
                    'traceback': ''.join(traceback.format_exception(exc_type, exc_val, exc_tb))
                }
                logger.log(
                    self.log_level,
                    f"Exception in context '{self.context_name}': {str(exc_val)}",
                    extra=error_info
                )
            
            # 调用错误处理函数
            if self.on_error is not None:
                try:
                    self.on_error(exc_val)
                except Exception as handler_error:
                    logger.error(
                        f"Error handler failed in context '{self.context_name}': {str(handler_error)}",
                        exc_info=True
                    )
            
            # 返回True表示抑制异常，False表示不抑制
            return not self.re_raise
        
        return False
    
    def has_error(self) -> bool:
        """
        检查是否发生了错误
        
        Returns:
            是否发生了错误
        """
        return self.exception is not None
    
    def get_error(self) -> Optional[Exception]:
        """
        获取捕获的异常
        
        Returns:
            捕获的异常或None
        """
        return self.exception


def safe_execute(
    func: Callable[..., T],
    *args: Any,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    安全执行函数
    
    Args:
        func: 要执行的函数
        *args: 位置参数
        **kwargs: 关键字参数
        
    Returns:
        包含执行结果的字典
        {"success": bool, "result": Any, "error": str, "exception": Exception}
    """
    start_time = get_current_timestamp()
    
    try:
        result = func(*args, **kwargs)
        
        return {
            "success": True,
            "result": result,
            "error": None,
            "exception": None,
            "execution_time": get_current_timestamp() - start_time
        }
    
    except Exception as e:
        return {
            "success": False,
            "result": None,
            "error": str(e),
            "exception": e,
            "traceback": traceback.format_exc(),
            "execution_time": get_current_timestamp() - start_time
        }
