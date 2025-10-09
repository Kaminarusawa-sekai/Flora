# memory/semantic.py
from memory.base_sqlite import SQLiteMemoryBase

class SemanticMemory(SQLiteMemoryBase):
    def __init__(self, user_id: str):
        schema = """
            CREATE TABLE IF NOT EXISTS semantic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fact TEXT,
                source TEXT
            )
        """
        super().__init__(f"{user_id}_semantic.db", "semantic_memory", schema)

    def add(self, fact: str, source: str = "user"):
        data = {"fact": fact, "source": source}
        self.insert(data)

    def query_by_keyword(self, keyword: str) -> list:
        # 简单模糊匹配，实际可结合向量搜索
        results = self.query("WHERE fact LIKE ?", (f"%{keyword}%",))
        return results



