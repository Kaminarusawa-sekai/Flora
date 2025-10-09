# memory/procedural.py
import json
from memory.base_sqlite import SQLiteMemoryBase

class ProceduralMemory(SQLiteMemoryBase):
    def __init__(self, user_id: str):
        schema = """
            CREATE TABLE IF NOT EXISTS procedural_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                steps TEXT,
                domain TEXT
            )
        """
        super().__init__(f"{user_id}_procedural.db", "procedural_memory", schema)

    def add(self, name: str, steps: list, domain: str = ""):
        data = {
            "name": name,
            "steps": json.dumps(steps),
            "domain": domain
        }
        self.insert(data)

    def query_by_name(self, name: str) -> dict:
        results = self.query("WHERE name = ?", (name,))
        if results:
            result = results[0]
            result["steps"] = json.loads(result["steps"])
            return result
        return None

    def query_by_domain(self, domain: str) -> list:
        results = self.query("WHERE domain = ?", (domain,))
        for r in results:
            r["steps"] = json.loads(r["steps"])
        return results



