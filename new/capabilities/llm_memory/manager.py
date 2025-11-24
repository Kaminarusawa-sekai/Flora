"""统一记忆管理器模块"""
from typing import Dict, Any, Optional, List
import time  # 用于测试时等待 embedding 完成

# 使用相对导入
from new.capabilities.capability_base import CapabilityBase
from new.capabilities.llm_memory.short_term import ShortTermMemory
from new.capabilities.llm_memory.resource_memory import ResourceMemory
from new.capabilities.llm_memory.vault_store import KnowledgeVault

# 导入 mem0
from mem0 import Memory
from config import MEM0_CONFIG

# === 全局共享的重量级资源（只初始化一次）===
SHARED_MEM0_CLIENT = Memory.from_config(MEM0_CONFIG)


from datetime import datetime
import json

class UnifiedMemoryManager:
    def __init__(self, user_id: str = "default", mem0_client=None):
        self.user_id = user_id
        self.mem0 = mem0_client or SHARED_MEM0_CLIENT
        self.stm = ShortTermMemory(max_history=10)  # 仍保留短期对话历史
        
        # 各专用存储（可 lazy init）
        self._procedural_store = None
        self._resource_store = None
        self._vault_store = VaultStore(user_id, vault_key) if vault_key else None

        self._core_cache = None

    # ======================
    # 1. 六类记忆写入接口
    # ======================

    @property
    def procedural_store(self):
        if self._procedural_store is None:
            self._procedural_store = ProceduralStore()
        return self._procedural_store

    @property
    def resource_store(self):
        if self._resource_store is None:
            self._resource_store = ResourceStore()
        return self._resource_store



    def add_core_memory(self, content: str):
        """核心记忆：用户基本信息、偏好"""
        self.mem0.add(
            content,
            user_id=self.user_id,
            metadata={"type": "core", "updated_at": datetime.now().isoformat()}
        )
        self._core_memory_cache = None  # 失效缓存

    def add_episodic_memory(self, content: str, timestamp: str = None):
        """情景记忆：具体事件"""
        meta = {
            "type": "episodic",
            "timestamp": timestamp or datetime.now().isoformat()
        }
        self.mem0.add(content, user_id=self.user_id, metadata=meta)

    def add_vault_memory(self, category: str, key_name: str, value: str):
        self.vault_store.store(self.user_id, category, key_name, value)

    def add_procedural_memory(self, domain: str, task_type: str, title: str, steps: List[str]):
        self.procedural_store.add_procedure(domain, task_type, title, steps)

    def add_resource_memory(self, file_path: str, summary: str, doc_type: str = "pdf"):
        self.resource_store.add_document(self.user_id, file_path, summary, doc_type)

    def add_semantic_memory(self, content: str, category: str = ""):
        """语义记忆：事实性知识"""
        meta = {"type": "semantic"}
        if category: meta["category"] = category
        self.mem0.add(content, user_id=self.user_id, metadata=meta)

    # ======================
    # 2. 记忆检索接口（按类型）
    # ======================

    def _search_by_type(self, memory_type: str, query: str = "", limit: int = 5):
        filters = {"type": memory_type, "user_id": self.user_id}
        if not query:
            query = "relevant information"  # Mem0 要求 query 非空
        results = self.mem0.search(
            query=query,
            filters=filters,
            limit=limit
        )
        return [r.get("memory", "") for r in results.get("results", [])]

    def get_core_memory(self) -> str:
        """获取核心记忆（缓存优化）"""
        if self._core_memory_cache is None:
            memories = self._search_by_type("core", limit=10)
            self._core_memory_cache = "\n".join(memories) if memories else ""
        return self._core_memory_cache

    def get_episodic_memory(self, query: str, limit: int = 3) -> str:
        return "\n".join(self._search_by_type("episodic", query, limit))

    # 修改检索方法
    def get_vault_memory(self, category: str = None) -> str:
        items = self.vault_store.retrieve(self.user_id, category)
        return "\n".join(items)

    def get_procedural_memory(self, query: str, domain: str = None) -> str:
        results = self.procedural_store.search(query, domain=domain, limit=2)
        return "\n\n".join(results)

    def get_resource_memory(self, query: str) -> str:
        docs = self.resource_store.search(query, self.user_id, limit=2)
        return "\n".join([
            f"[{d['filename']}]: {d['summary']} (ID: {d['id']})"
            for d in docs
        ])
    # ======================
    # 3. 上下文构建（供 LLM 使用）
    # ======================

    def build_system_prompt_context(self) -> str:
        """用于 system prompt 的核心记忆"""
        core = self.get_core_memory()
        return core if core else "无用户基本信息。"

    def build_task_context_for_llm(
        self,
        current_task: str,
        session_id: str = None,  # 可用于过滤 episodic
        include_vault: bool = False
    ) -> str:
        """
        为任务决策/规划构建完整上下文
        """
        parts = []

        # 1. 短期对话历史
        chat_hist = self.stm.format_history(n=6)
        if chat_hist.strip():
            parts.append(f"[近期对话]\n{chat_hist}")

        # 2. 核心记忆（始终包含）
        core = self.get_core_memory()
        if core:
            parts.append(f"[用户基本信息]\n{core}")

        # 3. 情景记忆（与当前任务相关）
        episodic = self.get_episodic_memory(current_task, limit=3)
        if episodic:
            parts.append(f"[相关经历]\n{episodic}")

        # 4. 程序记忆（操作指南）
        procedural = self.get_procedural_memory(current_task, limit=2)
        if procedural:
            parts.append(f"[操作指南]\n{procedural}")

        # 5. 语义记忆（事实知识）
        semantic = "\n".join(self._search_by_type("semantic", current_task, limit=3))
        if semantic:
            parts.append(f"[背景知识]\n{semantic}")

        # 6. 资源记忆
        resource = self.get_resource_memory(current_task)
        if resource:
            parts.append(f"[参考资料]\n{resource}")

        # 7. 敏感信息（按需）
        if include_vault:
            vault = self.get_vault_memory() if include_vault else ""
            if vault:
                parts.append(f"[敏感信息]\n{vault}")

        return "\n\n".join(parts) if parts else "无相关记忆。"

# ========================
# Capability 层：带缓存的 manager 管理
# ========================
class MemoryCapability(CapabilityBase):
    def __init__(self):
        super().__init__()
        # ⚠️ 仅用于测试/单机场景！生产环境需用外部缓存（如 Redis）或会话绑定
        self._manager_cache: Dict[str, UnifiedMemoryManager] = {}

    def get_capability_type(self) -> str:
        return "memory"

    def _get_manager(self, user_id: str) -> UnifiedMemoryManager:
        """按 user_id 缓存 manager 实例（解决 STM 生命周期问题）"""
        if user_id not in self._manager_cache:
            self._manager_cache[user_id] = UnifiedMemoryManager(
                user_id=user_id,
                mem0_client=SHARED_MEM0_CLIENT
            )
        return self._manager_cache[user_id]

    def execute(self, data: Dict[str, Any]) -> Dict[str, Any]:
        user_id = data.get("user_id")
        if not user_id or not isinstance(user_id, str):
            return {"success": False, "message": "user_id 是必需的字符串参数"}

        action = data.get("action", "").lower()
        try:
            if action == "store":
                return self._store(data, user_id)
            elif action == "retrieve":
                return self._retrieve(data, user_id)
            elif action == "delete":
                return self._delete(data, user_id)
            elif action == "clear":
                return self._clear(user_id)
            elif action == "ingest":
                return self._ingest(data, user_id)
            elif action == "search":
                return self._search(data, user_id)
            elif action == "build_context":
                return self._build_context(data, user_id)
            else:
                return {"success": False, "message": f"不支持的操作: {action}"}
        except Exception as e:
            return {"success": False, "message": f"内部错误: {str(e)}"}

    # --- 内部方法 ---
    def _store(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        key, value = data.get("key"), data.get("value")
        if key is None or value is None:
            return {"success": False, "message": "缺少 key 或 value"}
        manager = self._get_manager(user_id)
        success = manager.stm.store(key, value)
        return {"success": success, "message": "存储成功" if success else "失败"}

    def _retrieve(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        key = data.get("key")
        if key is None:
            return {"success": False, "message": "缺少 key"}
        manager = self._get_manager(user_id)
        value = manager.stm.retrieve(key)
        if value is not None:
            return {"success": True, "value": value}
        return {"success": False, "message": "未找到"}

    def _delete(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        key = data.get("key")
        if key is None:
            return {"success": False, "message": "缺少 key"}
        manager = self._get_manager(user_id)
        success = manager.stm.delete(key)
        return {"success": success, "message": "删除成功" if success else "失败"}

    def _clear(self, user_id: str) -> Dict[str, Any]:
        manager = self._get_manager(user_id)
        manager.clear_short_term()
        manager.resource_db.clear()
        manager.vault.clear()
        # 注意：Mem0 长期记忆不清除（符合设计）
        return {"success": True, "message": f"用户 {user_id} 的临时记忆已清空"}

    def _ingest(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        content = data.get("content")
        role = data.get("role", "user")
        if not content:
            return {"success": False, "message": "缺少 content"}
        manager = self._get_manager(user_id)
        manager.ingest(content, role)
        # 🧪 测试提示：Mem0 是异步的，立即搜索可能为空
        # 在真实应用中，应通过事件或延迟查询
        return {"success": True, "message": "信息已摄入（注意：长期记忆可能需要几秒生效）"}

    def _search(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        query = data.get("query")
        limit = data.get("limit", 5)
        if not query:
            return {"success": False, "message": "缺少 query"}
        manager = self._get_manager(user_id)
        results = manager.search_memories(query, limit)
        return {"success": True, "results": results}

    def _build_context(self, data: Dict[str, Any], user_id: str) -> Dict[str, Any]:
        query = data.get("query")
        manager = self._get_manager(user_id)
        context = manager.build_context_for_llm(query)
        return {"success": True, "context": context}