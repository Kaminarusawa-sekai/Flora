"""缓存工具模块"""
import time
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable, TypeVar, Generic, Tuple, List, Union
from collections import OrderedDict
from functools import wraps

from .logger import get_logger

logger = get_logger(__name__)

# 类型定义
K = TypeVar('K')  # 键类型
V = TypeVar('V')  # 值类型
T = TypeVar('T')  # 通用类型


class CacheStats:
    """
    缓存统计信息
    记录缓存的命中、未命中、添加、删除等操作次数
    """
    
    def __init__(self):
        """初始化缓存统计信息"""
        self.hits = 0  # 缓存命中次数
        self.misses = 0  # 缓存未命中次数
        self.adds = 0  # 添加缓存次数
        self.removals = 0  # 删除缓存次数
        self.evictions = 0  # 缓存驱逐次数
        self.expirations = 0  # 缓存过期次数
        self.lock = threading.RLock()  # 线程锁，确保线程安全
    
    def increment_hits(self) -> None:
        """增加命中计数"""
        with self.lock:
            self.hits += 1
    
    def increment_misses(self) -> None:
        """增加未命中计数"""
        with self.lock:
            self.misses += 1
    
    def increment_adds(self) -> None:
        """增加添加计数"""
        with self.lock:
            self.adds += 1
    
    def increment_removals(self) -> None:
        """增加删除计数"""
        with self.lock:
            self.removals += 1
    
    def increment_evictions(self) -> None:
        """增加驱逐计数"""
        with self.lock:
            self.evictions += 1
    
    def increment_expirations(self) -> None:
        """增加过期计数"""
        with self.lock:
            self.expirations += 1
    
    def get_hit_ratio(self) -> float:
        """
        获取缓存命中率
        
        Returns:
            缓存命中率（0-1之间的浮点数）
        """
        with self.lock:
            total = self.hits + self.misses
            return self.hits / total if total > 0 else 0.0
    
    def reset(self) -> None:
        """重置所有统计信息"""
        with self.lock:
            self.hits = 0
            self.misses = 0
            self.adds = 0
            self.removals = 0
            self.evictions = 0
            self.expirations = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """
        将统计信息转换为字典
        
        Returns:
            包含统计信息的字典
        """
        with self.lock:
            return {
                'hits': self.hits,
                'misses': self.misses,
                'adds': self.adds,
                'removals': self.removals,
                'evictions': self.evictions,
                'expirations': self.expirations,
                'hit_ratio': self.get_hit_ratio()
            }


class CacheEntry(Generic[K, V]):
    """
    缓存条目
    包含键、值、创建时间、过期时间等信息
    """
    
    def __init__(self, key: K, value: V, ttl: Optional[float] = None):
        """
        初始化缓存条目
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None表示永不过期
        """
        self.key = key
        self.value = value
        self.created_at = time.time()  # 创建时间
        self.ttl = ttl
        self.expires_at = self.created_at + ttl if ttl is not None else None
        self.last_accessed = self.created_at  # 最后访问时间
    
    def is_expired(self) -> bool:
        """
        检查条目是否已过期
        
        Returns:
            是否已过期
        """
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at
    
    def update_access(self) -> None:
        """更新最后访问时间"""
        self.last_accessed = time.time()
    
    def get_remaining_ttl(self) -> Optional[float]:
        """
        获取剩余生存时间
        
        Returns:
            剩余生存时间（秒），None表示永不过期或已过期
        """
        if self.expires_at is None:
            return None
        remaining = self.expires_at - time.time()
        return max(0, remaining) if remaining > 0 else None


class Cache(ABC, Generic[K, V]):
    """
    缓存抽象基类
    定义所有缓存实现必须提供的接口
    """
    
    def __init__(self, name: str = 'default'):
        """
        初始化缓存
        
        Args:
            name: 缓存名称，用于日志和标识
        """
        self.name = name
        self.stats = CacheStats()
        self.lock = threading.RLock()  # 线程锁，确保线程安全
    
    @abstractmethod
    def get(self, key: K) -> Optional[V]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值，如果不存在或已过期则返回None
        """
        pass
    
    @abstractmethod
    def set(self, key: K, value: V, ttl: Optional[float] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None表示永不过期
        """
        pass
    
    @abstractmethod
    def delete(self, key: K) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """清空所有缓存"""
        pass
    
    @abstractmethod
    def contains(self, key: K) -> bool:
        """
        检查缓存是否包含指定键
        
        Args:
            key: 缓存键
            
        Returns:
            是否包含指定键
        """
        pass
    
    @abstractmethod
    def size(self) -> int:
        """
        获取缓存大小
        
        Returns:
            缓存中项目的数量
        """
        pass
    
    def get_stats(self) -> CacheStats:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计信息对象
        """
        return self.stats
    
    def reset_stats(self) -> None:
        """重置缓存统计信息"""
        self.stats.reset()


class MemoryCache(Cache[K, V]):
    """
    内存缓存实现
    基于字典的简单内存缓存
    """
    
    def __init__(self, name: str = 'memory', max_size: Optional[int] = None):
        """
        初始化内存缓存
        
        Args:
            name: 缓存名称
            max_size: 最大缓存项数量，None表示无限制
        """
        super().__init__(name)
        self._cache: Dict[K, CacheEntry[K, V]] = {}
        self.max_size = max_size
    
    def get(self, key: K) -> Optional[V]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值，如果不存在或已过期则返回None
        """
        with self.lock:
            if key not in self._cache:
                self.stats.increment_misses()
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                self._cache.pop(key)
                self.stats.increment_expirations()
                self.stats.increment_misses()
                return None
            
            # 更新访问时间
            entry.update_access()
            self.stats.increment_hits()
            return entry.value
    
    def set(self, key: K, value: V, ttl: Optional[float] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None表示永不过期
        """
        with self.lock:
            # 检查是否需要驱逐
            if self.max_size is not None and len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_one()
            
            # 创建或更新缓存条目
            self._cache[key] = CacheEntry(key, value, ttl)
            self.stats.increment_adds()
    
    def delete(self, key: K) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self._cache:
                del self._cache[key]
                self.stats.increment_removals()
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self.lock:
            self._cache.clear()
            # 重置移除计数，但保持其他统计不变
            self.stats.removals = 0
    
    def contains(self, key: K) -> bool:
        """
        检查缓存是否包含指定键
        
        Args:
            key: 缓存键
            
        Returns:
            是否包含指定键
        """
        with self.lock:
            if key not in self._cache:
                return False
            
            # 检查是否过期
            entry = self._cache[key]
            if entry.is_expired():
                self._cache.pop(key)
                self.stats.increment_expirations()
                return False
            
            return True
    
    def size(self) -> int:
        """
        获取缓存大小
        
        Returns:
            缓存中项目的数量
        """
        with self.lock:
            # 清理过期项
            self._clean_expired()
            return len(self._cache)
    
    def _evict_one(self) -> None:
        """驱逐一个缓存项（默认驱逐最老的）"""
        if not self._cache:
            return
        
        # 找到最早创建的条目
        oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k].created_at)
        del self._cache[oldest_key]
        self.stats.increment_evictions()
    
    def _clean_expired(self) -> None:
        """清理所有过期的缓存项"""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        self.stats.expirations += len(expired_keys)


class LRUCache(Cache[K, V]):
    """
    最近最少使用缓存实现
    当缓存满时，优先驱逐最久未使用的项目
    """
    
    def __init__(self, name: str = 'lru', max_size: int = 1000):
        """
        初始化LRU缓存
        
        Args:
            name: 缓存名称
            max_size: 最大缓存项数量
        """
        super().__init__(name)
        self._cache = OrderedDict()  # 使用OrderedDict保持访问顺序
        self.max_size = max_size
    
    def get(self, key: K) -> Optional[V]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值，如果不存在或已过期则返回None
        """
        with self.lock:
            if key not in self._cache:
                self.stats.increment_misses()
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self.stats.increment_expirations()
                self.stats.increment_misses()
                return None
            
            # 将访问的项移到最后（表示最近使用）
            self._cache.move_to_end(key)
            entry.update_access()
            self.stats.increment_hits()
            return entry.value
    
    def set(self, key: K, value: V, ttl: Optional[float] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None表示永不过期
        """
        with self.lock:
            # 如果键已存在，先删除它（会在后面重新添加）
            if key in self._cache:
                del self._cache[key]
            # 如果缓存已满，驱逐最久未使用的项（OrderedDict的第一项）
            elif len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self.stats.increment_evictions()
            
            # 添加新项到最后
            self._cache[key] = CacheEntry(key, value, ttl)
            self.stats.increment_adds()
    
    def delete(self, key: K) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self._cache:
                del self._cache[key]
                self.stats.increment_removals()
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self.lock:
            self._cache.clear()
            self.stats.removals = 0
    
    def contains(self, key: K) -> bool:
        """
        检查缓存是否包含指定键
        
        Args:
            key: 缓存键
            
        Returns:
            是否包含指定键
        """
        with self.lock:
            if key not in self._cache:
                return False
            
            # 检查是否过期
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self.stats.increment_expirations()
                return False
            
            # 将访问的项移到最后
            self._cache.move_to_end(key)
            entry.update_access()
            return True
    
    def size(self) -> int:
        """
        获取缓存大小
        
        Returns:
            缓存中项目的数量
        """
        with self.lock:
            # 清理过期项
            self._clean_expired()
            return len(self._cache)
    
    def _clean_expired(self) -> None:
        """清理所有过期的缓存项"""
        expired_keys = [k for k, v in list(self._cache.items()) if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        self.stats.expirations += len(expired_keys)


class TTLCache(Cache[K, V]):
    """
    基于时间的缓存实现
    所有项目都有默认的生存时间
    """
    
    def __init__(self, name: str = 'ttl', default_ttl: float = 300.0, max_size: Optional[int] = None):
        """
        初始化TTL缓存
        
        Args:
            name: 缓存名称
            default_ttl: 默认生存时间（秒）
            max_size: 最大缓存项数量，None表示无限制
        """
        super().__init__(name)
        self._cache: Dict[K, CacheEntry[K, V]] = {}
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cleanup_interval = 60.0  # 自动清理间隔（秒）
        self._last_cleanup = time.time()
    
    def get(self, key: K) -> Optional[V]:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的值，如果不存在或已过期则返回None
        """
        with self.lock:
            # 检查是否需要自动清理
            self._maybe_cleanup()
            
            if key not in self._cache:
                self.stats.increment_misses()
                return None
            
            entry = self._cache[key]
            
            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self.stats.increment_expirations()
                self.stats.increment_misses()
                return None
            
            entry.update_access()
            self.stats.increment_hits()
            return entry.value
    
    def set(self, key: K, value: V, ttl: Optional[float] = None) -> None:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 生存时间（秒），None表示使用默认TTL
        """
        with self.lock:
            # 使用默认TTL
            effective_ttl = ttl if ttl is not None else self.default_ttl
            
            # 检查是否需要驱逐
            if self.max_size is not None and len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_one()
            
            # 创建或更新缓存条目
            self._cache[key] = CacheEntry(key, value, effective_ttl)
            self.stats.increment_adds()
    
    def delete(self, key: K) -> bool:
        """
        删除缓存值
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
        with self.lock:
            if key in self._cache:
                del self._cache[key]
                self.stats.increment_removals()
                return True
            return False
    
    def clear(self) -> None:
        """清空所有缓存"""
        with self.lock:
            self._cache.clear()
            self.stats.removals = 0
    
    def contains(self, key: K) -> bool:
        """
        检查缓存是否包含指定键
        
        Args:
            key: 缓存键
            
        Returns:
            是否包含指定键
        """
        with self.lock:
            if key not in self._cache:
                return False
            
            # 检查是否过期
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                self.stats.increment_expirations()
                return False
            
            entry.update_access()
            return True
    
    def size(self) -> int:
        """
        获取缓存大小
        
        Returns:
            缓存中项目的数量
        """
        with self.lock:
            # 清理过期项
            self._clean_expired()
            return len(self._cache)
    
    def _maybe_cleanup(self) -> None:
        """检查并可能执行自动清理"""
        current_time = time.time()
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._clean_expired()
            self._last_cleanup = current_time
    
    def _clean_expired(self) -> None:
        """清理所有过期的缓存项"""
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        for key in expired_keys:
            del self._cache[key]
        self.stats.expirations += len(expired_keys)
    
    def _evict_one(self) -> None:
        """驱逐一个缓存项（驱逐最早过期的）"""
        if not self._cache:
            return
        
        # 找到最早过期的条目
        # 对于永不过期的条目，将其视为很晚过期
        def get_expiry_time(k):
            entry = self._cache[k]
            return entry.expires_at if entry.expires_at is not None else float('inf')
        
        oldest_key = min(self._cache.keys(), key=get_expiry_time)
        del self._cache[oldest_key]
        self.stats.increment_evictions()


# 全局缓存字典，用于存储命名缓存实例
global_caches: Dict[str, Cache] = {}
global_caches_lock = threading.RLock()


def get_cache(name: str = 'default') -> Cache:
    """
    获取或创建一个全局缓存实例
    
    Args:
        name: 缓存名称
        
    Returns:
        缓存实例
    """
    with global_caches_lock:
        if name not in global_caches:
            # 默认使用LRU缓存
            global_caches[name] = LRUCache(name=name)
        return global_caches[name]


# 用于存储装饰器缓存信息的字典，键为函数对象，值为缓存配置
_cache_decorator_info: Dict[Callable, Dict[str, Any]] = {}
_cache_decorator_lock = threading.RLock()


def cache(
    func: Optional[Callable[..., T]] = None,
    ttl: Optional[float] = None,
    cache_name: str = 'default',
    key_generator: Optional[Callable[..., str]] = None
) -> Union[Callable[[Callable[..., T]], Callable[..., T]], Callable[..., T]]:
    """
    缓存装饰器
    缓存函数的返回值，避免重复计算
    
    Args:
        func: 要装饰的函数
        ttl: 缓存生存时间（秒），None表示永不过期
        cache_name: 使用的缓存名称
        key_generator: 自定义缓存键生成器函数
        
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # 获取缓存实例
        cache_instance = get_cache(cache_name)
        
        # 保存缓存信息
        with _cache_decorator_lock:
            _cache_decorator_info[func] = {
                'cache': cache_instance,
                'cache_name': cache_name,
                'ttl': ttl
            }
        
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            # 生成缓存键
            if key_generator is not None:
                cache_key = key_generator(*args, **kwargs)
            else:
                # 默认键生成：使用函数名、参数的字符串表示
                # 注意：这种方式可能不完美，但适用于大多数情况
                key_parts = [func.__qualname__]
                
                # 添加位置参数
                for arg in args:
                    # 尝试获取可哈希的表示
                    try:
                        # 如果是对象实例，只使用其类型和id
                        if hasattr(arg, '__dict__'):
                            key_parts.append(f"{type(arg).__name__}@{id(arg)}")
                        else:
                            # 对于基本类型，直接使用
                            key_parts.append(str(arg))
                    except Exception:
                        # 如果无法序列化，使用对象id
                        key_parts.append(f"object@{id(arg)}")
                
                # 添加关键字参数（按键排序确保一致性）
                for k, v in sorted(kwargs.items()):
                    try:
                        if hasattr(v, '__dict__'):
                            key_parts.append(f"{k}={type(v).__name__}@{id(v)}")
                        else:
                            key_parts.append(f"{k}={v}")
                    except Exception:
                        key_parts.append(f"{k}=object@{id(v)}")
                
                cache_key = ":".join(key_parts)
            
            # 尝试从缓存获取
            result = cache_instance.get(cache_key)
            if result is not None:
                return result
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache_instance.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    
    # 支持不带参数的调用方式
    if func is None:
        return decorator
    return decorator(func)


def invalidate_cache(
    func: Optional[Callable] = None,
    cache_name: Optional[str] = None,
    key: Optional[str] = None
) -> None:
    """
    使缓存失效
    
    Args:
        func: 要使缓存失效的函数（如果使用了装饰器）
        cache_name: 要清空的缓存名称
        key: 要删除的特定缓存键
    """
    if func is not None:
        # 使特定函数的缓存信息失效
        with _cache_decorator_lock:
            if func in _cache_decorator_info:
                info = _cache_decorator_info[func]
                cache_instance = info['cache']
                # 如果提供了键，只删除特定键
                if key is not None:
                    cache_instance.delete(key)
                else:
                    # 否则重新创建缓存实例（这会清空所有内容）
                    # 注意：这是一个简化的实现，实际上无法仅清除特定函数的所有缓存
                    # 在真实应用中，可能需要更复杂的缓存键管理
                    pass
    elif cache_name is not None:
        # 清空整个缓存
        with global_caches_lock:
            if cache_name in global_caches:
                global_caches[cache_name].clear()
    elif key is not None:
        # 删除特定键（从默认缓存）
        default_cache = get_cache()
        default_cache.delete(key)
    else:
        # 没有提供任何参数，记录警告
        logger.warning("invalidate_cache called without any parameters")
