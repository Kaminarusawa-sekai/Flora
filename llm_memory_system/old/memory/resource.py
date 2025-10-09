# memory/resource.py
import json
from memory.base_sqlite import SQLiteMemoryBase

class ResourceMemory(SQLiteMemoryBase):
    def __init__(self, user_id: str):
        schema = """
            CREATE TABLE IF NOT EXISTS resource_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                content TEXT,
                metadata TEXT
            )
        """
        super().__init__(f"{user_id}_resource.db", "resource_memory", schema)

    def add(self, title: str, content: str, metadata: dict = None):
        data = {
            "title": title,
            "content": content,
            "metadata": json.dumps(metadata or {})
        }
        self.insert(data)

    def query_by_title(self, title: str) -> dict:
        results = self.query("WHERE title = ?", (title,))
        if results:
            result = results[0]
            result["metadata"] = json.loads(result["metadata"])
            return result
        return None



