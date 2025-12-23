import logging 
from typing import Dict, Any, Optional
from mem0 import Memory
from .interface import IMemoryCapability

# 导入自定义 Qwen embedding
from .qwen_embedding import QwenEmbedding
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
            }
        }
        """
        mem0_config = config.get("mem0", {})
        if not mem0_config:
            print("[INFO] 使用 Qwen (OpenAI 兼容模式 - 环境变量版) + Chroma 配置")
            default_path = "./data/memory_chroma"
            Path(default_path).mkdir(parents=True, exist_ok=True)
            
            # 获取阿里云 Key
            dashscope_api_key = os.getenv("DASHSCOPE_API_KEY")
            
            # ====== 关键步骤 1：设置 OpenAI 标准环境变量 ======
            # mem0 的底层 SDK 会自动读取这些变量，从而连接到阿里云
            # 这样我们就不需要在 config 字典里传 base_url，避免了校验报错
            os.environ["OPENAI_API_KEY"] = dashscope_api_key
            os.environ["OPENAI_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"

            mem0_config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "user_memories",
                        "path": default_path,
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

        # 现在 config 里没有非法参数了，BaseEmbedderConfig 校验会通过
        self.client = Memory.from_config(mem0_config)

        print(f"[INFO] Mem0 已初始化，配置 keys: {list(mem0_config.keys())}")

    def shutdown(self) -> None:
        pass

    def get_capability_type(self) -> str:
        return "mem0_memory"

    def search_memories(self, user_id: str, query: str, limit: int = 5) -> str:
        if not self.client:
            return "记忆服务未初始化。"
        try:
            results = self.client.search(query, user_id=user_id, limit=limit)
            if not results["results"]:
                return "暂无相关记忆。"
            return "\n".join([f"- {m['memory']}" for m in results])
        except Exception as e:
            logger.error(f"搜索记忆时出错: {str(e)}")
            return "记忆服务暂不可用。"

    def add_memory(self, user_id: str, text: str) -> None:
        if self.client:
            self.client.add(text, user_id=user_id)
            print(f"   [MemoryDB] 已异步存入记忆: {text[:20]}...")