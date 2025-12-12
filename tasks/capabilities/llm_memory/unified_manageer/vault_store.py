# vault_store.py
import sqlite3
import os
from typing import List, Optional

class VaultStore:
    def __init__(self, db_path: str = "vault.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    key_name TEXT NOT NULL,
                    value TEXT NOT NULL,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def store(self, user_id: str, category: str, key_name: str, value: str):
        # ⚠️ 明文存储！仅用于开发/测试
        print("[DEV WARNING] 敏感信息以明文存入 SQLite！")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO vault (user_id, category, key_name, value) VALUES (?, ?, ?, ?)",
                (user_id, category, key_name, value)
            )
            conn.commit()

    def retrieve(self, user_id: str, category: Optional[str] = None) -> List[str]:
        with sqlite3.connect(self.db_path) as conn:
            if category:
                cur = conn.execute(
                    "SELECT key_name, value FROM vault WHERE user_id = ? AND category = ?",
                    (user_id, category)
                )
            else:
                cur = conn.execute(
                    "SELECT key_name, value FROM vault WHERE user_id = ?",
                    (user_id,)
                )
            return [f"{row[0]}: {row[1]}" for row in cur.fetchall()]