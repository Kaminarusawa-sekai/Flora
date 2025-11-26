
import sqlite3
# ========================
# Resource 实现
# ========================
class SQLiteResourceDAO:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    doc_type TEXT,
                    summary TEXT,
                    storage_path TEXT,
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def insert(self, doc_id: str, user_id: str, filename: str, doc_type: str,
               summary: str, storage_path: str, source_url: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO resources
                   (id, user_id, filename, doc_type, summary, storage_path, source_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, user_id, filename, doc_type, summary, storage_path, source_url)
            )
            conn.commit()

    def search(self, query: str, user_id: str, limit: int = 3):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """SELECT id, filename, summary, storage_path
                   FROM resources
                   WHERE user_id = ? AND summary LIKE ?
                   LIMIT ?""",
                (user_id, f"%{query}%", limit)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_by_id(self, doc_id: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM resources WHERE id = ?", (doc_id,))
            row = cur.fetchone()
            return dict(row) if row else None
