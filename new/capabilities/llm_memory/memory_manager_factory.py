# memory_factory.py

import threading
from functools import lru_cache, wraps
from typing import Optional, Any, Dict

from your_module.memory_manager import UnifiedMemoryManager  # 替换为你的实际路径
from your_module.config import config
from your_module.repositories import (
    create_vault_repo,
    create_procedural_repo,
    create_resource_repo,
)
from your_module.clients import get_shared_qwen_client, get_shared_mem0_client  # 假设你有这些

# 全局共享的底层依赖（初始化一次）
_SHARED_VAULT_REPO = create_vault_repo(config["vault"])
_SHARED_PROCEDURAL_REPO = create_procedural_repo(config["procedural"])
_SHARED_RESOURCE_REPO = create_resource_repo(config["resource"])
_SHARED_QWEN_CLIENT = get_shared_qwen_client()
_SHARED_MEM0_CLIENT = get_shared_mem0_client()


class MemoryManagerFactory:
    """
    用户级 UnifiedMemoryManager 工厂，带 LRU 缓存和懒加载。
    
    使用示例：
        factory = MemoryManagerFactory(maxsize=1000)
        manager = factory.get_manager("user_123")
    """

    def __init__(self, maxsize: int = 1000):
        if maxsize <= 0:
            raise ValueError("maxsize must be positive")
        self.maxsize = maxsize
        self._cache_lock = threading.RLock()  # 支持重入，兼容 lru_cache
        self._init_lru_cache()

    def _init_lru_cache(self):
        """动态创建带指定 maxsize 的 LRU 缓存方法"""
        @lru_cache(maxsize=self.maxsize)
        def _get_manager_cached(user_id: str) -> UnifiedMemoryManager:
            return UnifiedMemoryManager(
                user_id=user_id,
                vault_repo=_SHARED_VAULT_REPO,
                procedural_repo=_SHARED_PROCEDURAL_REPO,
                resource_repo=_SHARED_RESOURCE_REPO,
                mem0_client=_SHARED_MEM0_CLIENT,
                qwen_client=_SHARED_QWEN_CLIENT,
            )
        self._get_manager_cached = _get_manager_cached

    def get_manager(self, user_id: str) -> UnifiedMemoryManager:
        """
        获取指定用户的 MemoryManager（线程安全）
        """
        if not isinstance(user_id, str) or not user_id.strip():
            raise ValueError("user_id must be a non-empty string")
        user_id = user_id.strip()
        
        with self._cache_lock:
            return self._get_manager_cached(user_id)

    def evict_user(self, user_id: str) -> bool:
        """
        显式从缓存中移除某个用户的 manager（例如用户登出时）
        返回是否成功移除
        """
        with self._cache_lock:
            try:
                self._get_manager_cached.cache_clear()  # lru_cache 不支持单 key 清除
                return True
            except Exception:
                return False

    def cache_info(self) -> dict:
        """返回缓存统计信息"""
        with self._cache_lock:
            info = self._get_manager_cached.cache_info()
            return {
                "hits": info.hits,
                "misses": info.misses,
                "maxsize": info.maxsize,
                "currsize": info.currsize,
            }

    def clear_cache(self):
        """清空整个缓存（谨慎使用）"""
        with self._cache_lock:
            self._get_manager_cached.cache_clear()


# ======================
# 全局单例（推荐方式）
# ======================


##TODO: 所有单例集中创建与管理
# 创建全局工厂实例（可根据配置调整 maxsize）
GLOBAL_MEMORY_FACTORY: MemoryManagerFactory = MemoryManagerFactory(
    maxsize=config.get("memory_manager_cache_size", 2000)
)


# ======================
# 便捷函数（可选）
# ======================

def get_user_memory_manager(user_id: str) -> UnifiedMemoryManager:
    """快捷获取用户记忆管理器"""
    return GLOBAL_MEMORY_FACTORY.get_manager(user_id)