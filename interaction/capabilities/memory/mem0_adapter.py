from typing import Dict, Any
from mem0 import Memory
from .interface import IMemoryService


class Mem0MemoryService(IMemoryService):
    """
    Mem0记忆服务适配器，实现IMemoryService接口
    """
    def __init__(self):
        # 初始化 Mem0 实例
        self.client = None

    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化Mem0客户端
        """
        self.client = Memory(**config.get('mem0', {}))

    def shutdown(self) -> None:
        """
        关闭资源（如果需要）
        """
        pass

    def get_capability_type(self) -> str:
        """
        返回能力类型
        """
        return "memory"

    def search_memories(self, user_id: str, query: str, limit: int = 5) -> str:
        """
        调用 Mem0 的搜索接口
        """
        if not self.client:
            return "记忆服务未初始化。"
        
        results = self.client.search(query, user_id=user_id, limit=limit)
        if not results:
            return "暂无相关记忆。"
        # 将结果格式化为易于 LLM 阅读的文本
        return "\n".join([f"- {m['memory']}" for m in results])

    def add_memory(self, user_id: str, text: str) -> None:
        """
        调用 Mem0 的添加接口
        """
        if self.client:
            self.client.add(text, user_id=user_id)
            print(f"   [MemoryDB] 已异步存入记忆: {text[:20]}...")
