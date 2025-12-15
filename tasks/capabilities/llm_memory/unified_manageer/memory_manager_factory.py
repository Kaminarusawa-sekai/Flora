# memory_factory.py

import threading
from functools import lru_cache, wraps
from typing import Optional, Any, Dict

from .manager import UnifiedMemoryManager  # 替换为你的实际路径
from ...capbility_config import CapabilityConfig

# 避免循环导入，将导入移到函数内部


# 全局共享的底层依赖（延迟初始化）
_SHARED_VAULT_REPO = None
_SHARED_PROCEDURAL_REPO = None
_SHARED_RESOURCE_REPO = None




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
        
        def _init_shared_repos():
            """初始化共享仓库"""
            global _SHARED_VAULT_REPO, _SHARED_PROCEDURAL_REPO, _SHARED_RESOURCE_REPO
            if _SHARED_VAULT_REPO is None:
                from ....external.memory_store.memory_repos import (
                    build_procedural_repo,
                    build_resource_repo,
                    build_vault_repo
                )
                _SHARED_VAULT_REPO = build_vault_repo()
                _SHARED_PROCEDURAL_REPO = build_procedural_repo()
                _SHARED_RESOURCE_REPO = build_resource_repo()
        
        @lru_cache(maxsize=self.maxsize)
        def _get_manager_cached(user_id: str) -> UnifiedMemoryManager:
            # 在创建管理器之前确保共享仓库已初始化
            _init_shared_repos()
            return UnifiedMemoryManager(
                user_id=user_id,
                vault_repo=_SHARED_VAULT_REPO,
                procedural_repo=_SHARED_PROCEDURAL_REPO,
                resource_repo=_SHARED_RESOURCE_REPO,
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


# ##TODO: 所有单例集中创建与管理
# # 创建全局工厂实例（可根据配置调整 maxsize）
# GLOBAL_MEMORY_FACTORY: MemoryManagerFactory = MemoryManagerFactory(
#     maxsize=config.get("memory_manager_cache_size", 2000)
# )


# # ======================
# # 便捷函数（可选）
# # ======================

# def get_user_memory_manager(user_id: str) -> UnifiedMemoryManager:
#     """快捷获取用户记忆管理器"""
#     return GLOBAL_MEMORY_FACTORY.get_manager(user_id)