# resource_store.py
import os
import sqlite3
import uuid
from datetime import datetime
from minio import Minio
from minio.error import S3Error
from typing import List, Dict, Optional

class ResourceStore:
    def __init__(
        self,
        sqlite_path: str = "resources.db",
        use_minio: bool = True,
        minio_client: Optional[Minio] = None,
        local_dir: str = "resource_files"
    ):
        self.sqlite_path = sqlite_path
        self.use_minio = use_minio
        self.minio = minio_client
        self.local_dir = local_dir
        if not use_minio:
            os.makedirs(local_dir, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS resources (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    doc_type TEXT,
                    summary TEXT,
                    storage_path TEXT,  -- local path 或 minio object name
                    source_url TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_document(
        self,
        user_id: str,
        file_path: str,
        summary: str,
        doc_type: str = "unknown",
        source_url: str = ""
    ) -> str:
        doc_id = str(uuid.uuid4())
        filename = os.path.basename(file_path)

        if self.use_minio and self.minio:
            # 上传到 MinIO
            bucket = "user-resources"
            object_name = f"{user_id}/{doc_id}/{filename}"
            try:
                self.minio.fput_object(bucket, object_name, file_path)
                storage_path = f"minio://{bucket}/{object_name}"
            except S3Error as e:
                raise RuntimeError(f"MinIO upload failed: {e}")
        else:
            # 存本地
            dest_path = os.path.join(self.local_dir, user_id, doc_id, filename)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            import shutil
            shutil.copy2(file_path, dest_path)
            storage_path = dest_path

        # 记录元数据
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute(
                """INSERT INTO resources
                   (id, user_id, filename, doc_type, summary, storage_path, source_url)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (doc_id, user_id, filename, doc_type, summary, storage_path, source_url)
            )
            conn.commit()

        return doc_id

    def search(self, query: str, user_id: str, limit: int = 3) -> List[Dict]:
        """
        简化版：按 summary 模糊匹配（未来可加 embedding）
        """
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(
                """SELECT id, filename, summary, storage_path
                   FROM resources
                   WHERE user_id = ?
                   AND summary LIKE ?
                   LIMIT ?""",
                (user_id, f"%{query}%", limit)
            )
            return [dict(row) for row in cur.fetchall()]

    def get_by_id(self, doc_id: str) -> Optional[Dict]:
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute("SELECT * FROM resources WHERE id = ?", (doc_id,))
            row = cur.fetchone()
            return dict(row) if row else None