# external/memory_repos.py
from ...capabilities.llm_memory.unified_manageer.memory_interfaces import IVaultRepository, IProceduralRepository, IResourceRepository

from .filebased_procedural_repository import FileBasedProceduralRepository
from .sqLite_vault_dao import SQLiteVaultDAO
from .sqlite_resource_dao import SQLiteResourceDAO
from .security import Encryptor
from .encrypte_vault_repository import EncryptedVaultRepository
from .resource_repository import ResourceRepository
from .storage import get_minio_client   # ← 统一获取 MinIO 客户端
from config import MEMORY_CONFIG          # ← 从系统统一配置读取
# ========================
# 工厂函数
# ========================
def build_vault_repo() -> IVaultRepository:
    config = MEMORY_CONFIG["vault"]
    dao = SQLiteVaultDAO(config["db_path"])
    encryptor = Encryptor(config.get("encryption_key_b64"))
    return EncryptedVaultRepository(dao, encryptor)

def build_procedural_repo() -> IProceduralRepository:
    config = MEMORY_CONFIG["procedural"]
    return FileBasedProceduralRepository(config["dir"])

def build_resource_repo() -> IResourceRepository:
    config = MEMORY_CONFIG["resource"]
    dao = SQLiteResourceDAO(config["db_path"])
    minio_client = get_minio_client() if config.get("use_minio") else None
    return ResourceRepository(
        dao=dao,
        use_minio=config.get("use_minio", False),
        minio_client=minio_client,
        local_dir=config.get("local_dir")
    )