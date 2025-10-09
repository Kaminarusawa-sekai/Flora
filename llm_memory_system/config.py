# memory/config.py
import os

# DashScope (Qwen) API Key
os.environ["DASHSCOPE_API_KEY"] = os.getenv("DASHSCOPE_API_KEY")

# Mem0 配置
MEM0_CONFIG = {
    "vector_store": {
        "provider": "chroma",
        "config": {
            "collection_name": "user_memories",
            "path": "./chroma_db",  # 本地存储路径
        },
    },
    "llm": {
        "provider": "qwen",  # 支持 Qwen！
        "config": {
            "model": "qwen-plus",  # 或 qwen-turbo
            "temperature": 0.1,
            "max_tokens": 4096,
        },
    },
    "memory": {
        "type": "graph",  # 可选: "vector" 或 "graph"
        "enable_reasoning": True,  # 启用推理式记忆提取
    },
    "embedder": {
        "provider": "qwen",  # 使用 Qwen 的 embedding 模型
        "config": {
            "model": "text-embedding-v2"
        }
    }
}