# memory/episodic.py
import json
from memory.base_sqlite import SQLiteMemoryBase
from datetime import datetime

class EpisodicMemory(SQLiteMemoryBase):
    def __init__(self, user_id: str):
        schema = """
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event TEXT,
                timestamp TEXT,
                tags TEXT
            )
        """
        super().__init__(f"{user_id}_episodic.db", "episodic_memory", schema)

    def add(self, event: str, timestamp: str = None, tags: list = None):
        data = {
            "event": event,
            "timestamp": timestamp or datetime.now().isoformat(),
            "tags": json.dumps(tags or [])
        }
        self.insert(data)

    def get_recent(self, n: int = 5) -> list:
        results = self.query("ORDER BY timestamp DESC LIMIT ?", (n,))
        for r in results:
            r["tags"] = json.loads(r["tags"])
        return results



