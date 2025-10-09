# memory/core.py
import os
from memory.base_sqlite import SQLiteMemoryBase

class CoreMemory(SQLiteMemoryBase):
    def __init__(self, user_id: str):
        schema = """
            CREATE TABLE IF NOT EXISTS core_memory (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """
        super().__init__(f"{user_id}_core.db", "core_memory", schema)

    def add(self, key: str, value: str):
        from datetime import datetime
        now = datetime.now().isoformat()
        data = {"key": key, "value": value, "updated_at": now}
        self.insert(data)

    def get(self, key: str) -> str:
        results = self.query("WHERE key = ?", (key,))
        return results[0]["value"] if results else None

    def get_all(self) -> dict:
        results = self.query()
        return {row["key"]: row["value"] for row in results}

    def to_prompt_string(self) -> str:
        pairs = [f"{k}: {v}" for k, v in self.get_all().items()]
        return "; ".join(pairs) if pairs else ""



