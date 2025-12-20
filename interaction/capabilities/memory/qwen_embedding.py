# interaction/capabilities/memory/qwen_embedding.py

import dashscope
from dashscope import TextEmbedding
from typing import List, Optional

class QwenEmbedding:
    """
    Qwen Embedding 适配器，用于 Mem0
    支持 DashScope 的 text-embedding-v1 / v2 模型
    """

    def __init__(self, model: str = "text-embedding-v2", api_key: Optional[str] = None):
        self.model = model
        if api_key:
            dashscope.api_key = api_key
        # 否则自动使用环境变量 DASHSCOPE_API_KEY

    def embed(self, text: str, purpose: str = "search") -> List[float]:
        """
        生成文本的 embedding 向量
        :param text: 输入文本
        :param purpose: 用途（Mem0 会传，但 DashScope 不需要）
        :return: embedding 向量 (list of float)
        """
        try:
            response = TextEmbedding.call(
                model=self.model,
                input=text
            )
            if response.status_code == 200:
                # DashScope 返回格式: {"output": {"embeddings": [{"embedding": [...]}]}}
                embedding = response.output["embeddings"][0]["embedding"]
                return embedding
            else:
                raise RuntimeError(f"DashScope API error: {response.code} - {response.message}")
        except Exception as e:
            raise RuntimeError(f"Failed to get embedding from Qwen (DashScope): {e}")