"""资源管理工具模块"""
import logging
import threading
import contextlib
from typing import Any, Callable, Dict, List, Optional, TypeVar, Generic
from collections import defaultdict

from .logger import get_logger
from .error_handling import ErrorContext
from .singleton import Singleton

logger = get_logger(__name__)

T = TypeVar('T')


class ResourceManager(Singleton):
    """
    资源管理器
    用于管理系统中的共享资源，确保资源的正确分配和释放
    实现了单例模式
    """
    
    def __init__(self):
        """初始化资源管理器"""
        # 资源池字典，格式: {resource_type: {resource_id: resource}}
        self._resource_pools: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # 资源锁定字典，用于保护每个资源类型的访问
        self._locks: Dict[str, threading.RLock] = defaultdict(threading.RLock)
        
        # 资源创建函数字典
        self._creators: Dict[str, Callable[..., Any]] = {}
        
        # 资源清理函数字典
        self._cleaners: Dict[str, Callable[[Any], None]] = {}
        
        # 线程本地存储，用于跟踪当前线程持有的资源
        self._thread_resources = threading.local()
        
        # 资源使用计数
        self._usage_counts: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    
    def register_resource_type(
        self,
        resource_type: str,
        creator_func: Callable[..., Any],
        cleaner_func: Optional[Callable[[Any], None]] = None
    ) -> None:
        """
        注册资源类型
        
        Args:
            resource_type: 资源类型名称
            creator_func: 创建资源的函数
            cleaner_func: 清理资源的函数，如果为None则使用默认清理
        """
        with self._locks['manager']:
            self._creators[resource_type] = creator_func
            self._cleaners[resource_type] = cleaner_func
            logger.info(f"Registered resource type: {resource_type}")
    
    def get_resource(
        self,
        resource_type: str,
        resource_id: str,
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """
        获取或创建资源
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            *args: 创建资源时的参数
            **kwargs: 创建资源时的关键字参数
            
        Returns:
            资源对象
            
        Raises:
            ValueError: 如果资源类型未注册
            Exception: 如果创建资源失败
        """
        # 检查资源类型是否已注册
        if resource_type not in self._creators:
            raise ValueError(f"Resource type '{resource_type}' not registered")
        
        # 获取资源类型的锁
        with self._locks[resource_type]:
            # 检查资源是否已存在
            if resource_id in self._resource_pools[resource_type]:
                resource = self._resource_pools[resource_type][resource_id]
                self._usage_counts[resource_type][resource_id] += 1
                logger.debug(f"Retrieved existing resource: {resource_type}:{resource_id}")
            else:
                # 创建新资源
                try:
                    logger.info(f"Creating new resource: {resource_type}:{resource_id}")
                    resource = self._creators[resource_type](*args, **kwargs)
                    self._resource_pools[resource_type][resource_id] = resource
                    self._usage_counts[resource_type][resource_id] = 1
                    
                    # 记录到线程本地存储
                    self._add_thread_resource(resource_type, resource_id)
                    
                except Exception as e:
                    logger.error(f"Failed to create resource {resource_type}:{resource_id}: {str(e)}")
                    raise
            
            return resource
    
    def release_resource(
        self,
        resource_type: str,
        resource_id: str
    ) -> bool:
        """
        释放资源
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            
        Returns:
            是否成功释放
        """
        with self._locks[resource_type]:
            # 检查资源是否存在
            if resource_type not in self._resource_pools or resource_id not in self._resource_pools[resource_type]:
                logger.warning(f"Resource not found: {resource_type}:{resource_id}")
                return False
            
            # 减少使用计数
            if self._usage_counts[resource_type][resource_id] > 0:
                self._usage_counts[resource_type][resource_id] -= 1
            
            # 从线程本地存储中移除
            self._remove_thread_resource(resource_type, resource_id)
            
            # 如果使用计数为0，清理资源
            if self._usage_counts[resource_type][resource_id] == 0:
                try:
                    resource = self._resource_pools[resource_type][resource_id]
                    
                    # 调用清理函数
                    if resource_type in self._cleaners and self._cleaners[resource_type]:
                        logger.info(f"Cleaning resource: {resource_type}:{resource_id}")
                        self._cleaners[resource_type](resource)
                    
                    # 从资源池移除
                    del self._resource_pools[resource_type][resource_id]
                    del self._usage_counts[resource_type][resource_id]
                    
                    logger.info(f"Released resource: {resource_type}:{resource_id}")
                    return True
                    
                except Exception as e:
                    logger.error(f"Error releasing resource {resource_type}:{resource_id}: {str(e)}")
                    return False
            
            return True
    
    @contextlib.contextmanager
    def use_resource(
        self,
        resource_type: str,
        resource_id: str,
        *args: Any,
        **kwargs: Any
    ):
        """
        上下文管理器，用于安全地使用资源
        确保资源在使用完毕后被正确释放
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
            *args: 创建资源时的参数
            **kwargs: 创建资源时的关键字参数
        """
        resource = None
        try:
            resource = self.get_resource(resource_type, resource_id, *args, **kwargs)
            yield resource
        finally:
            if resource is not None:
                self.release_resource(resource_type, resource_id)
    
    def close_all_resources(
        self,
        resource_type: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        关闭所有资源
        
        Args:
            resource_type: 资源类型，如果为None则关闭所有类型的资源
            
        Returns:
            关闭失败的资源列表，格式: {resource_type: [resource_ids]}
        """
        failed_resources: Dict[str, List[str]] = defaultdict(list)
        
        # 确定要关闭的资源类型
        types_to_close = [resource_type] if resource_type else list(self._resource_pools.keys())
        
        for rt in types_to_close:
            if rt not in self._resource_pools:
                continue
            
            # 复制资源ID列表，避免在迭代时修改字典
            resource_ids = list(self._resource_pools[rt].keys())
            
            for rid in resource_ids:
                # 设置使用计数为0，强制清理
                self._usage_counts[rt][rid] = 0
                if not self.release_resource(rt, rid):
                    failed_resources[rt].append(rid)
        
        if failed_resources:
            logger.warning(f"Some resources failed to close: {failed_resources}")
        else:
            logger.info(f"Successfully closed all resources")
        
        return failed_resources
    
    def get_resource_info(
        self,
        resource_type: Optional[str] = None
    ) -> Dict[str, Dict[str, int]]:
        """
        获取资源使用信息
        
        Args:
            resource_type: 资源类型，如果为None则返回所有类型
            
        Returns:
            资源使用情况，格式: {resource_type: {resource_id: usage_count}}
        """
        if resource_type:
            return {resource_type: dict(self._usage_counts.get(resource_type, {}))}
        else:
            return {rt: dict(counts) for rt, counts in self._usage_counts.items()}
    
    def _add_thread_resource(
        self,
        resource_type: str,
        resource_id: str
    ) -> None:
        """
        将资源添加到线程本地存储
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
        """
        if not hasattr(self._thread_resources, 'resources'):
            self._thread_resources.resources = defaultdict(list)
        
        resource_key = f"{resource_type}:{resource_id}"
        if resource_key not in self._thread_resources.resources[resource_type]:
            self._thread_resources.resources[resource_type].append(resource_id)
    
    def _remove_thread_resource(
        self,
        resource_type: str,
        resource_id: str
    ) -> None:
        """
        从线程本地存储中移除资源
        
        Args:
            resource_type: 资源类型
            resource_id: 资源ID
        """
        if hasattr(self._thread_resources, 'resources'):
            if resource_type in self._thread_resources.resources:
                try:
                    self._thread_resources.resources[resource_type].remove(resource_id)
                    # 如果该类型没有资源了，清理该类型
                    if not self._thread_resources.resources[resource_type]:
                        del self._thread_resources.resources[resource_type]
                except ValueError:
                    pass  # 资源可能已经被移除
    
    def get_thread_resources(self) -> Dict[str, List[str]]:
        """
        获取当前线程持有的所有资源
        
        Returns:
            当前线程持有的资源列表
        """
        if hasattr(self._thread_resources, 'resources'):
            return dict(self._thread_resources.resources)
        return {}
    
    def release_thread_resources(self) -> Dict[str, List[str]]:
        """
        释放当前线程持有的所有资源
        
        Returns:
            释放失败的资源列表
        """
        failed_resources: Dict[str, List[str]] = defaultdict(list)
        
        if hasattr(self._thread_resources, 'resources'):
            # 复制资源信息，避免在迭代时修改
            resources_copy = dict(self._thread_resources.resources)
            
            for resource_type, resource_ids in resources_copy.items():
                for resource_id in resource_ids:
                    if not self.release_resource(resource_type, resource_id):
                        failed_resources[resource_type].append(resource_id)
        
        return failed_resources


class ResourcePool(Generic[T]):
    """
    资源池
    用于管理一组相同类型的资源，支持资源的借用和归还
    """
    
    def __init__(
        self,
        create_func: Callable[..., T],
        max_size: int = 10,
        validate_func: Optional[Callable[[T], bool]] = None,
        destroy_func: Optional[Callable[[T], None]] = None
    ):
        """
        初始化资源池
        
        Args:
            create_func: 创建资源的函数
            max_size: 资源池最大大小
            validate_func: 验证资源是否有效的函数
            destroy_func: 销毁资源的函数
        """
        self._create_func = create_func
        self._max_size = max_size
        self._validate_func = validate_func
        self._destroy_func = destroy_func
        
        # 可用资源队列
        self._available_resources: List[T] = []
        
        # 锁，确保线程安全
        self._lock = threading.RLock()
        
        # 当前创建的资源数量
        self._created_count = 0
    
    def acquire(self, *args: Any, **kwargs: Any) -> T:
        """
        获取资源
        
        Args:
            *args: 创建资源时的参数
            **kwargs: 创建资源时的关键字参数
            
        Returns:
            资源对象
        """
        with self._lock:
            # 尝试从可用资源中获取
            while self._available_resources:
                resource = self._available_resources.pop()
                
                # 验证资源是否有效
                if not self._validate_func or self._validate_func(resource):
                    logger.debug(f"Acquired existing resource")
                    return resource
                else:
                    # 资源无效，销毁并继续获取
                    self._destroy_resource(resource)
            
            # 如果没有可用资源且未达到最大大小，创建新资源
            if self._created_count < self._max_size:
                resource = self._create_resource(*args, **kwargs)
                return resource
            
            # 如果达到最大大小，抛出异常
            raise RuntimeError(f"Resource pool reached maximum size ({self._max_size})")
    
    def release(self, resource: T) -> None:
        """
        释放资源回池
        
        Args:
            resource: 要释放的资源
        """
        with self._lock:
            # 验证资源是否有效
            if not self._validate_func or self._validate_func(resource):
                self._available_resources.append(resource)
                logger.debug(f"Resource returned to pool")
            else:
                # 资源无效，销毁
                self._destroy_resource(resource)
    
    def _create_resource(self, *args: Any, **kwargs: Any) -> T:
        """
        创建资源
        
        Args:
            *args: 创建资源时的参数
            **kwargs: 创建资源时的关键字参数
            
        Returns:
            资源对象
            
        Raises:
            Exception: 如果创建失败
        """
        try:
            resource = self._create_func(*args, **kwargs)
            self._created_count += 1
            logger.debug(f"Created new resource (total: {self._created_count})")
            return resource
        except Exception as e:
            logger.error(f"Failed to create resource: {str(e)}")
            raise
    
    def _destroy_resource(self, resource: T) -> None:
        """
        销毁资源
        
        Args:
            resource: 要销毁的资源
        """
        try:
            if self._destroy_func:
                self._destroy_func(resource)
            self._created_count -= 1
            logger.debug(f"Destroyed resource (total: {self._created_count})")
        except Exception as e:
            logger.error(f"Failed to destroy resource: {str(e)}")
    
    def clear(self) -> None:
        """
        清空资源池，销毁所有资源
        """
        with self._lock:
            while self._available_resources:
                resource = self._available_resources.pop()
                self._destroy_resource(resource)
    
    @property
    def size(self) -> int:
        """
        获取当前创建的资源数量
        
        Returns:
            资源数量
        """
        with self._lock:
            return self._created_count
    
    @property
    def available_count(self) -> int:
        """
        获取当前可用的资源数量
        
        Returns:
            可用资源数量
        """
        with self._lock:
            return len(self._available_resources)


# 创建全局资源管理器实例
global_resource_manager = ResourceManager()