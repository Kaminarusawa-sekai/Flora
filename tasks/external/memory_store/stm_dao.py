# stm_dao.py
import sqlite3
import time
from typing import List, Dict, Optional

class STMRecordDAO:
    def __init__(self, db_path: str = "memory.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stm_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON stm_records(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON stm_records(created_at)")

    def add_message(self, user_id: str, role: str, content: str):
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO stm_records (user_id, role, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (user_id, role, content, now, now)
            )

    def get_recent_messages(self, user_id: str, limit: int = 10) -> List[Dict[str, str]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT role, content 
                FROM stm_records 
                WHERE user_id = ?
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (user_id, limit)
            )
            rows = cursor.fetchall()
            # 注意：SQL 是 DESC，所以要 reverse 回时间顺序
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def get_recent_messages_by_scope(self, scope_prefix: str, limit: int = 10) -> List[Dict[str, str]]:
        like_pattern = f"{scope_prefix}:%"
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                SELECT role, content
                FROM stm_records
                WHERE user_id = ? OR user_id LIKE ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (scope_prefix, like_pattern, limit)
            )
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]

    def clear_user_history(self, user_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM stm_records WHERE user_id = ?", (user_id,))

    def cleanup_old_records(self, max_age_seconds: int = 86400 * 7):  # 默认保留7天
        cutoff = time.time() - max_age_seconds
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM stm_records WHERE created_at < ?", (cutoff,))