"""单例模式实现"""
import threading
from typing import Any, TypeVar, Type, Dict

T = TypeVar('T')


class Singleton:
    """
    单例模式的基类
    通过继承此类，可以确保一个类只有一个实例
    
    使用方法:
    ```python
    class MyClass(Singleton):
        def __init__(self, value=None):
            self.value = value
    ```
    
    特性:
    - 线程安全
    - 支持延迟初始化
    - 支持继承关系
    """
    
    # 存储单例实例的字典
    _instances: Dict[Type['Singleton'], 'Singleton'] = {}
    
    # 线程锁，确保线程安全
    _lock = threading.RLock()
    
    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """
        重写__new__方法，确保只创建一个实例
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            类的唯一实例
        """
        with cls._lock:
            if cls not in cls._instances:
                # 创建新实例
                instance = super(Singleton, cls).__new__(cls)
                # 存储实例
                cls._instances[cls] = instance
        
        return cls._instances[cls]
    
    @classmethod
    def get_instance(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """
        获取类的单例实例，如果不存在则创建
        
        Args:
            *args: 创建实例时的参数
            **kwargs: 创建实例时的关键字参数
            
        Returns:
            类的单例实例
        """
        return cls(*args, **kwargs)
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例，通常用于测试
        """
        with cls._lock:
            if cls in cls._instances:
                del cls._instances[cls]
    
    @classmethod
    def has_instance(cls) -> bool:
        """
        检查是否已经创建了实例
        
        Returns:
            是否已经创建了实例
        """
        return cls in cls._instances
    
    @classmethod
    def get_all_instances(cls) -> Dict[Type['Singleton'], 'Singleton']:
        """
        获取所有Singleton子类的实例
        
        Returns:
            所有实例的字典
        """
        return cls._instances.copy()

    @classmethod
    def clear_singletons(cls) -> None:
        """
        清除所有Singleton实例
        通常用于测试目的
        """
        with cls._lock:
            cls._instances.clear()


class LazySingleton:
    """
    懒加载单例模式
    只有在第一次访问时才会创建实例
    
    使用方法:
    ```python
    class MyClass(LazySingleton):
        def __init__(self):
            self.value = "initialized"
    ```
    """
    
    _instance = None
    _lock = threading.RLock()
    _initialized = False
    
    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """
        重写__new__方法，实现懒加载
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            类的实例
        """
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(LazySingleton, cls).__new__(cls)
        
        return cls._instance
    
    def __init_subclass__(cls) -> None:
        """
        为子类重置初始化状态
        """
        cls._instance = None
        cls._initialized = False
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例
        """
        with cls._lock:
            cls._instance = None
            cls._initialized = False
    
    @classmethod
    def is_initialized(cls) -> bool:
        """
        检查实例是否已经初始化
        
        Returns:
            是否已经初始化
        """
        return cls._initialized


def singleton(cls):
    """
    单例模式装饰器
    
    使用方法:
    ```python
    @singleton
    class MyClass:
        pass
    ```
    """
    instances = {}
    lock = threading.Lock()
    
    def get_instance(*args, **kwargs):
        with lock:
            if cls not in instances:
                instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    
    return get_instance

class ThreadLocalSingleton:
    """
    线程本地单例模式
    每个线程拥有独立的实例
    
    使用方法:
    ```python
    class MyClass(ThreadLocalSingleton):
        def __init__(self):
            self.thread_id = threading.get_ident()
    ```
    """
    
    _thread_local = threading.local()
    
    def __new__(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """
        为每个线程创建独立的实例
        
        Args:
            *args: 位置参数
            **kwargs: 关键字参数
            
        Returns:
            线程本地的实例
        """
        # 获取当前线程的标识符
        thread_id = threading.get_ident()
        
        # 初始化线程本地字典
        if not hasattr(cls._thread_local, 'instances'):
            cls._thread_local.instances = {}
        
        # 如果当前线程还没有实例，创建一个
        if thread_id not in cls._thread_local.instances:
            instance = super(ThreadLocalSingleton, cls).__new__(cls)
            cls._thread_local.instances[thread_id] = instance
        
        return cls._thread_local.instances[thread_id]
    
    @classmethod
    def get_thread_instance(cls: Type[T], *args: Any, **kwargs: Any) -> T:
        """
        获取当前线程的实例
        
        Args:
            *args: 参数
            **kwargs: 关键字参数
            
        Returns:
            当前线程的实例
        """
        return cls(*args, **kwargs)
    
    @classmethod
    def clear_thread_instance(cls) -> None:
        """
        清除当前线程的实例
        """
        thread_id = threading.get_ident()
        if hasattr(cls._thread_local, 'instances'):
            if thread_id in cls._thread_local.instances:
                del cls._thread_local.instances[thread_id]
    
    @classmethod
    def clear_all_instances(cls) -> None:
        """
        清除所有线程的实例
        """
        if hasattr(cls._thread_local, 'instances'):
            cls._thread_local.instances.clear()
