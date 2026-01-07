import logging
from typing import Dict, Any, Optional, List
from mem0 import Memory
from .interface import IMemoryCapability

# 导入自定义 Qwen embedding
from .qwen_embedding import QwenEmbedding
from external.rag import DifyRagClient
import os
from pathlib import Path

logger = logging.getLogger(__name__)
class Mem0Memory(IMemoryCapability):
    """
    Mem0记忆服务适配器
    支持 OpenAI 或 Qwen (DashScope) 作为 embedding provider
    """
    def __init__(self):
        self.client: Optional[Memory] = None
        self.rag_client: Optional[DifyRagClient] = None
        self.rag_top_k = 3

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化 Mem0 客户端
        配置示例:
        {
            "mem0": {
                "embedding_provider": "qwen",  # 可选: "openai" | "qwen"
                "embedding_model": "text-embedding-v2",
                "api_key": "your_dashscope_key",  # 可选，推荐用环境变量
                "vector_store": { ... },
                ...
            },
            "rag": {
                "api_key": "your_dify_api_key",
                "dataset_id": "your_dataset_id",
                "base_url": "https://api.dify.ai/v1",
                "enabled": true
            }
        }
        """
        # 直接使用传入的配置，不再从环境变量构建默认配置
        mem0_config = config.get("mem0", {})
        self.rag_config = config.get("rag", {})
        rag_config = self.rag_config
        # ====== 关键步骤 1：设置 OpenAI 标准环境变量 ======
        # mem0 的底层 SDK 会自动读取这些变量，从而连接到阿里云
        # 这样我们就不需要在 config 字典里传 base_url，避免了校验报错
        # 获取阿里云 Key
        dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
        os.environ["OPENAI_API_KEY"] = dashscope_api_key
        os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        # 如果mem0_config为空，使用空字典，让Mem0 SDK使用默认配置
        if not mem0_config:
            print("[INFO] 使用 Qwen (OpenAI 兼容模式 - 环境变量版) + Chroma 配置")
            default_path = "./data/memory_chroma"
            Path(default_path).mkdir(parents=True, exist_ok=True)
            
            
            
            
            

            mem0_config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "user_memories",
                        "path": "./data/memory_chroma",
                    },
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        # ====== 关键步骤 2：精简 Config ======
                        # 只保留库支持的标准参数 'model'
                        # 不要在这里写 'base_url' 或 'api_key' (除非库强制要求 api_key)
                        "model": "text-embedding-v2"
                    }
                },
                "memory": {
                    "type": "graph",
                    "enable_reasoning": True,
                },
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": "qwen-plus"
                        # 同样，base_url 和 api_key 交给环境变量处理
                    }
                }
            }
            # 确保向量存储路径存在
            Path(mem0_config["vector_store"]["config"]["path"]).mkdir(parents=True, exist_ok=True)

        # 现在 config 里没有非法参数了，BaseEmbedderConfig 校验会通过
        self.client = Memory.from_config(mem0_config)

        print(f"[INFO] Mem0 已初始化，配置 keys: {list(mem0_config.keys())}")

        self._init_rag_client(rag_config)

    def _init_rag_client(self, rag_config: Dict[str, Any]) -> None:
        # 严格使用传入的配置，不再从环境变量获取
        api_key = rag_config.get("api_key")
        dataset_id = rag_config.get("dataset_id")
        base_url = rag_config.get("base_url")
        endpoint = rag_config.get("endpoint")
        enabled = rag_config.get("enabled", True)

        if not enabled:
            return

        if not api_key:
            logger.info("Dify RAG 未配置 api_key，跳过初始化。")
            return

        self.rag_top_k = rag_config.get("top_k", self.rag_top_k)
        self.rag_client = DifyRagClient(
            api_key=api_key,
            base_url=base_url,
            dataset_id=dataset_id,
            endpoint=endpoint,
        )

    def shutdown(self) -> None:
        pass

    def get_capability_type(self) -> str:
        return "mem0_memory"

    def search_memories(self, user_id: str, query: str, limit: int = 5) -> str:
        if not self.client:
            return "记忆服务未初始化。"
        try:
            results = self.client.search(query, user_id=user_id, limit=limit)
            items = self._extract_results(results)
            rag_items = self._search_rag(query=query, user_id=user_id, limit=limit)
            if not items and not rag_items:
                core_items = self._get_core_items(user_id=user_id, limit=limit)
                if not core_items:
                    return "暂无相关记忆。"
                items = core_items
            combined = items + rag_items
            return "\n".join([f"- {self._format_memory(m)}" for m in combined])
        except Exception as e:
            logger.error(f"搜索记忆时出错: {str(e)}")
            return "记忆服务暂不可用。"

    def add_memory(self, user_id: str, text: str) -> None:
        if self.client:
            self.client.add(text, user_id=user_id, metadata={"type": "conversation"})
            print(f"   [MemoryDB] 已异步存入记忆: {text[:20]}...")

    def list_core_memories(self, user_id: str, limit: int = 50):
        """获取用户核心记忆列表
        
        Args:
            user_id: 用户唯一标识
            limit: 返回的记忆数量限制，默认50条
        
        Returns:
            list[dict]: 核心记忆列表，每条记忆包含以下字段：
                - id (str): 记忆唯一标识符，从 mem0 客户端返回的记忆项中提取
                - key (str): 记忆的键名，从记忆项的 metadata 中获取
                - value (str): 记忆的内容值，经过格式化处理的记忆文本
        
        实现逻辑：
        1. 检查 mem0 客户端是否初始化
        2. 调用 _get_core_items 获取用户核心记忆项
        3. 遍历记忆项，提取并格式化所需字段
        4. 返回格式化后的核心记忆列表
        """
        if not self.client:
            return []
        items = self._get_core_items(user_id=user_id, limit=limit)
        results = []
        for item in items:
            meta = item.get("metadata", {}) if isinstance(item, dict) else {}
            results.append({
                "id": self._get_memory_id(item),
                "key": meta.get("key", ""),
                "value": self._format_memory(item),
            })
        return results

    def set_core_memory(self, user_id: str, key: str, value: str) -> None:
        if not self.client:
            return
        existing = self._find_core_memory_by_key(user_id=user_id, key=key)
        if existing:
            memory_id = self._get_memory_id(existing)
            if memory_id:
                self.client.update(memory_id, {"memory": value, "metadata": {"type": "core", "key": key}})
                return
        self.client.add(value, user_id=user_id, metadata={"type": "core", "key": key})

    def delete_core_memory(self, user_id: str, key: str) -> None:
        if not self.client:
            return
        existing = self._find_core_memory_by_key(user_id=user_id, key=key)
        memory_id = self._get_memory_id(existing) if existing else None
        if memory_id:
            self.client.delete(memory_id)

    def _get_core_items(self, user_id: str, limit: int = 50):
        if not self.client:
            return []
        results = self.client.get_all(user_id=user_id, filters={"type": "core"}, limit=limit)
        return self._extract_results(results)

    def _search_rag(self, query: str, user_id: str, limit: int) -> List[Dict[str, Any]]:
        if not self.rag_client:
            return []
        rag_results = self.rag_client.search(query=query, user_id=user_id, top_k=min(limit, self.rag_top_k))
        formatted: List[Dict[str, Any]] = []
        for item in rag_results:
            formatted.append({
                "memory": item.get("text", ""),
                "metadata": {
                    "type": "rag",
                    "score": item.get("score"),
                }
            })
        return formatted

    @staticmethod
    def _extract_results(results):
        if results is None:
            return []
        if isinstance(results, dict):
            items = results.get("results")
            if isinstance(items, list):
                return items
        if isinstance(results, list):
            return results
        return []

    @staticmethod
    def _get_memory_id(item):
        if not isinstance(item, dict):
            return None
        return item.get("id") or item.get("memory_id")

    @staticmethod
    def _format_memory(item) -> str:
        if not isinstance(item, dict):
            return str(item)
        meta = item.get("metadata", {}) or {}
        text = item.get("memory") or item.get("text") or item.get("content") or ""
        if meta.get("type") == "core" and meta.get("key"):
            return f"{meta['key']}: {text}"
        return text

    def _find_core_memory_by_key(self, user_id: str, key: str):
        items = self._get_core_items(user_id=user_id, limit=100)
        for item in items:
            meta = item.get("metadata", {}) if isinstance(item, dict) else {}
            if meta.get("key") == key:
                return item
        return None
