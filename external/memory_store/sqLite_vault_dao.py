import sqlite3
from typing import Optional

class SQLiteVaultDAO:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS vault (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    category TEXT,
                    key_name TEXT NOT NULL,
                    encrypted_value BLOB NOT NULL
                )
            """)
            conn.commit()

    def insert(self, user_id: str, category: str, key_name: str, encrypted_value: bytes):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO vault (user_id, category, key_name, encrypted_value) VALUES (?, ?, ?, ?)",
                (user_id, category, key_name, encrypted_value)
            )
            conn.commit()

    def select(self, user_id: str, category: Optional[str] = None):
        with sqlite3.connect(self.db_path) as conn:
            if category:
                cur = conn.execute(
                    "SELECT key_name, encrypted_value FROM vault WHERE user_id = ? AND category = ?",
                    (user_id, category)
                )
            else:
                cur = conn.execute(
                    "SELECT key_name, encrypted_value FROM vault WHERE user_id = ?",
                    (user_id,)
                )
            return cur.fetchall()
