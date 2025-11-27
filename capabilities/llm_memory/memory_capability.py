
# ========================
# Capability 层：带缓存的 manager 管理
# ========================
import threading
import logging
from typing import Optional, Dict, Any, List
from abc import ABC
from cachetools import TTLCache

from ..capability_base import CapabilityBase
from .manager import UnifiedMemoryManager, SHARED_MEM0_CLIENT
from .memory_interfaces import (
    IVaultRepository,
    IProceduralRepository,
    IResourceRepository
)
from ..llm.qwen_adapter import QwenAdapter


logger = logging.getLogger(__name__)


class MemoryCapability(CapabilityBase):
    """
    记忆能力组件：为指定用户/智能体提供统一记忆管理能力。
    
    职责：
    - 按 user_id 缓存并复用 UnifiedMemoryManager 实例
    - 代理常用记忆操作接口
    - 隔离上层逻辑与记忆系统实现细节
    
    使用方式：
        cap = MemoryCapability(user_id="user_123")
        cap.initialize()
        cap.add_memory_intelligently("我喜欢喝茶")
        context = cap.build_conversation_context("当前对话")
    """

    # 类级缓存：所有实例共享，按 user_id 复用 manager
    _manager_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)
    _cache_lock = threading.Lock()

    def __init__(
        self,
        user_id: str,
        vault_repo: Optional[IVaultRepository] = None,
        procedural_repo: Optional[IProceduralRepository] = None,
        resource_repo: Optional[IResourceRepository] = None,
        mem0_client=None,
        qwen_client=None,
        cache_ttl: int = 3600,
        cache_maxsize: int = 500
    ):
        if not user_id or not isinstance(user_id, str):
            raise ValueError("user_id must be a non-empty string")

        # 初始化基类（会调用 get_capability_name）
        super().__init__()

        self.user_id = user_id
        self._vault_repo = vault_repo
        self._procedural_repo = procedural_repo
        self._resource_repo = resource_repo
        self._mem0_client = mem0_client
        self._qwen_client = qwen_client

        # 动态配置缓存（仅首次有效）
        with self._cache_lock:
            if len(self._manager_cache) == 0:
                self._manager_cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)

        self._memory_manager: Optional[UnifiedMemoryManager] = None

    def get_capability_type(self) -> str:
        return "memory"

    def initialize(self) -> bool:
        """初始化记忆能力，获取或创建 UnifiedMemoryManager 实例"""
        if self.is_initialized:
            return True

        try:
            with self._cache_lock:
                if self.user_id in self._manager_cache:
                    self._memory_manager = self._manager_cache[self.user_id]
                    logger.debug(f"Reusing cached UnifiedMemoryManager for user={self.user_id}")
                else:
                    logger.info(f"Creating new UnifiedMemoryManager for user={self.user_id}")
                    self._memory_manager = UnifiedMemoryManager(
                        user_id=self.user_id,
                        vault_repo=self._vault_repo,
                        procedural_repo=self._procedural_repo,
                        resource_repo=self._resource_repo,
                        mem0_client=self._mem0_client or SHARED_MEM0_CLIENT,
                        qwen_client=self._qwen_client or QwenAdapter()
                    )
                    self._manager_cache[self.user_id] = self._memory_manager

            self.is_initialized = True
            return True

        except Exception as e:
            logger.error(f"Failed to initialize MemoryCapability for user={self.user_id}: {e}", exc_info=True)
            self.is_initialized = False
            return False

    def shutdown(self) -> None:
        """关闭能力（不销毁缓存中的 manager，仅标记状态）"""
        super().shutdown()  # 调用基类，设置 is_initialized=False
        logger.debug(f"MemoryCapability shutdown for user={self.user_id}")

    # ==============================
    # 代理常用记忆接口（封装 UnifiedMemoryManager）
    # ==============================

    def add_memory_intelligently(self, content: str) -> None:
        self._ensure_initialized()
        self._memory_manager.add_memory_intelligently(content)

    def build_conversation_context(self, current_input: str = "") -> str:
        self._ensure_initialized()
        return self._memory_manager.build_conversation_context(current_input)

    def build_planning_context(self, planning_goal: str) -> str:
        self._ensure_initialized()
        return self._memory_manager.build_planning_context(planning_goal)

    def build_execution_context(self, task_description: str, include_sensitive: bool = False) -> str:
        self._ensure_initialized()
        return self._memory_manager.build_execution_context(task_description, include_sensitive)

    def get_core_memory(self) -> str:
        self._ensure_initialized()
        return self._memory_manager.get_core_memory()

    def _ensure_initialized(self):
        if not self.is_initialized:
            raise RuntimeError(
                f"MemoryCapability '{self.name}' for user '{self.user_id}' is not initialized. "
                "Call initialize() first."
            )

    # ==============================
    # 扩展状态信息（覆盖基类方法）
    # ==============================

    def get_status(self) -> Dict[str, Any]:
        base_status = super().get_status()
        cache_hit = self.user_id in self._manager_cache
        base_status.update({
            'user_id': self.user_id,
            'cache_hit': cache_hit,
            'cache_size': len(self._manager_cache),
        })
        return base_status

    # ==============================
    # 类方法：用于监控
    # ==============================

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        return {
            'current_size': len(cls._manager_cache),
            'max_size': cls._manager_cache.maxsize,
            'ttl': cls._manager_cache.ttl,
        }