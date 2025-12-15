from pathlib import Path
import shutil
import os
from typing import Dict, Any, Optional, List, TYPE_CHECKING
import uuid

# 只在类型检查时导入，避免运行时循环导入
if TYPE_CHECKING:
    from .sqlite_resource_dao import SQLiteResourceDAO
    from ...capabilities.llm_memory.unified_manageer.memory_interfaces import IResourceRepository

class ResourceRepository:
    def __init__(self, dao: 'SQLiteResourceDAO', use_minio: bool, minio_client=None, local_dir: str = None):
        self.dao = dao
        self.use_minio = use_minio
        self.minio = minio_client
        self.local_dir = local_dir
        if local_dir:
            Path(local_dir).mkdir(parents=True, exist_ok=True)

    def add_document(self, user_id: str, file_path: str, summary: str, doc_type: str = "unknown", source_url: str = ""):
        doc_id = str(uuid.uuid4())
        filename = os.path.basename(file_path)

        if self.use_minio and self.minio:
            bucket = "user-resources"
            object_name = f"{user_id}/{doc_id}/{filename}"
            self.minio.fput_object(bucket, object_name, file_path)
            storage_path = f"minio://{bucket}/{object_name}"
        else:
            dest = Path(self.local_dir) / user_id / doc_id / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file_path, dest)
            storage_path = str(dest)

        self.dao.insert(doc_id, user_id, filename, doc_type, summary, storage_path, source_url)
        return doc_id

    def search(self, query: str, user_id: str, limit: int = 3) -> List[Dict[str, Any]]:
        return self.dao.search(query, user_id, limit)

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        return self.dao.get_by_id(doc_id)