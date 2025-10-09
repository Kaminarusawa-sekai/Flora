# memory/vault.py
from memory.base_sqlite import SQLiteMemoryBase
# 注意：实际生产中应加密存储敏感信息
class KnowledgeVault(SQLiteMemoryBase):
    def __init__(self, user_id: str):
        schema = """
            CREATE TABLE IF NOT EXISTS knowledge_vault (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """
        super().__init__(f"{user_id}_vault.db", "knowledge_vault", schema)

    def add(self, key: str, value: str):
        data = {"key": key, "value": value}
        self.insert(data)

    def get(self, key: str) -> str:
        results = self.query("WHERE key = ?", (key,))
        return results[0]["value"] if results else None



