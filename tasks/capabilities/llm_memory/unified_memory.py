
# ========================
# Capability 层：带缓存的 manager 管理
# ========================
import threading
import logging
from typing import Optional, Dict, Any, List
from abc import ABC
from cachetools import TTLCache

from .interface import IMemoryCapability
from .unified_manageer.manager import UnifiedMemoryManager, SHARED_MEM0_CLIENT
from .unified_manageer.memory_interfaces import (
    IVaultRepository,
    IProceduralRepository,
    IResourceRepository
)
from .unified_manageer.memory_manager_factory import (
    MemoryManagerFactory,
)


# 避免循环导入，将全局变量改为延迟初始化
_SHARED_VAULT_REPO = None
_SHARED_PROCEDURAL_REPO = None
_SHARED_RESOURCE_REPO = None

# 延迟初始化函数
def _init_shared_repos():
    global _SHARED_VAULT_REPO, _SHARED_PROCEDURAL_REPO, _SHARED_RESOURCE_REPO
    if _SHARED_VAULT_REPO is None:
        from ...external.memory_store.memory_repos import (
            build_procedural_repo,
            build_resource_repo,
            build_vault_repo
        )
        _SHARED_VAULT_REPO = build_vault_repo()
        _SHARED_PROCEDURAL_REPO = build_procedural_repo()
        _SHARED_RESOURCE_REPO = build_resource_repo()


logger = logging.getLogger(__name__)


class UnifiedMemory(IMemoryCapability):
    """
    记忆能力组件：为指定用户/智能体提供统一记忆管理能力。
    
    职责：
    - 按 user_id 缓存并复用 UnifiedMemoryManager 实例
    - 代理常用记忆操作接口
    - 隔离上层逻辑与记忆系统实现细节
    
    使用方式：
        cap = MemoryCapability(user_id="user_123")
        cap.initialize({})
        cap.add_memory_intelligently("我喜欢喝茶")
        context = cap.build_conversation_context("当前对话")
    """

    # 类级缓存：所有实例共享，按 user_id 复用 manager
    _manager_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)
    _cache_lock = threading.Lock()

    def __init__(
        self,
        vault_repo: Optional[IVaultRepository] = None,
        procedural_repo: Optional[IProceduralRepository] = None,
        resource_repo: Optional[IResourceRepository] = None,
        mem0_client=None,
        qwen_client=None,
        cache_ttl: int = 3600,
        cache_maxsize: int = 500
    ):
        super().__init__()
        # if not user_id or not isinstance(user_id, str):
        #     raise ValueError("user_id must be a non-empty string")
        
        self.factory: Optional[MemoryManagerFactory] = None
        # self.user_id = user_id
        self._vault_repo = vault_repo
        self._procedural_repo = procedural_repo
        self._resource_repo = resource_repo
        self._mem0_client = mem0_client
        self._qwen_client = qwen_client
        self.is_initialized = False

        # 动态配置缓存（仅首次有效）
        with self._cache_lock:
            if len(self._manager_cache) == 0:
                self._manager_cache = TTLCache(maxsize=cache_maxsize, ttl=cache_ttl)

        self._memory_manager: Optional[UnifiedMemoryManager] = None

    def get_capability_type(self) -> str:
        return "unified_memory"

    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化记忆能力，获取或创建 UnifiedMemoryManager 实例"""
        if self.is_initialized:
            return

        try:
            with self._cache_lock:
                # if self.user_id in self._manager_cache:
                #     self._memory_manager = self._manager_cache[self.user_id]
                #     logger.debug(f"Reusing cached UnifiedMemoryManager for user={self.user_id}")
                # else:
                # 初始化共享仓库
                _init_shared_repos()
                logger.info(f"Creating new UnifiedMemoryManager ")
                self._memory_manager = UnifiedMemoryManager(
                    vault_repo=self._vault_repo or _SHARED_VAULT_REPO,
                    procedural_repo=self._procedural_repo or _SHARED_PROCEDURAL_REPO,
                    resource_repo=self._resource_repo or _SHARED_RESOURCE_REPO,
                    mem0_client=self._mem0_client or SHARED_MEM0_CLIENT,
                    qwen_client=self._qwen_client 
                )
                

            self.is_initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize MemoryCapability: {e}", exc_info=True)
            self.is_initialized = False

        # """
        # 初始化：读取配置 -> 初始化Repos -> 初始化工厂
        # Args:
        #     config: config.json -> capabilities -> memory -> core_memory
        # """
        # if config is None:
        #     config = {}
        # self.is_initialized = True
        # # 1. 初始化共享的 Repositories (这些通常也是单例)
        # # 你的工厂代码里用了 _SHARED_VAULT_REPO，建议在这里显式初始化并注入给工厂
        # # 或者是初始化全局变量（取决于你的 Repo 实现方式）
        # # self._init_global_repos(config) 

        # # 2. 获取配置参数
        # cache_size = config.get("cache_size", 1000)
        
        # # 3. 实例化工厂
        # # 注意：这里我们让 Capability 持有工厂实例，而不是用全局变量 GLOBAL_MEMORY_FACTORY
        # # 这样更符合依赖注入的设计，方便测试和解耦
        # self.factory = MemoryManagerFactory(maxsize=cache_size)
        
        print(f"MemoryCapability initialized ")

    def shutdown(self) -> None:
        """关闭能力（不销毁缓存中的 manager，仅标记状态）"""
        self.is_initialized = False
        logger.debug(f"MemoryCapability shutdown ")

    # ==============================
    # 代理常用记忆操作接口（封装 UnifiedMemoryManager）
    # ==============================

    def add_memory_intelligently(self, user_id: str, content: Any, metadata: Dict = None) -> None:
        self._ensure_initialized()
        self._memory_manager.add_memory_intelligently(user_id, content, metadata)

    def retrieve_relevant_memory(self, user_id: str, query: str) -> str:
        self._ensure_initialized()
        # 假设 UnifiedMemoryManager 有类似的方法，如果没有则需要实现
        return self._memory_manager.build_conversation_context(user_id, query)

    def build_conversation_context(self, user_id: str, current_input: str = "") -> str:
        self._ensure_initialized()
        return self._memory_manager.build_conversation_context(user_id, current_input)

    def build_planning_context(self, user_id: str, planning_goal: str) -> str:
        self._ensure_initialized()
        return self._memory_manager.build_planning_context(user_id, planning_goal)

    def build_execution_context(self, user_id: str, task_description: str, include_sensitive: bool = False) -> str:
        self._ensure_initialized()
        return self._memory_manager.build_execution_context(user_id, task_description, include_sensitive)

    def get_core_memory(self, user_id: str) -> str:
        self._ensure_initialized()
        return self._memory_manager.get_core_memory(user_id)

    def _ensure_initialized(self):
        if not self.is_initialized:
            raise RuntimeError(
                f"MemoryCapability   is not initialized. "
                "Call initialize() first."
            )

    # ==============================
    # 扩展状态信息（覆盖基类方法）
    # ==============================

    def get_status(self) -> Dict[str, Any]:
        base_status = super().get_status()
        # cache_hit = self.user_id in self._manager_cache
        base_status.update({
            # 'user_id': self.user_id,
            # 'cache_hit': cache_hit,
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