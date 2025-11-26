from typing import List, Optional
from new.capabilities.llm_memory.memory_interfaces import IVaultRepository
from new.external.memory_store.sqLite_vault_dao import SQLiteVaultDAO
from new.external.memory_store.security import Encryptor

class EncryptedVaultRepository(IVaultRepository):
    def __init__(self, dao: SQLiteVaultDAO, encryptor: Encryptor):
        self.dao = dao
        self.encryptor = encryptor

    def store(self, user_id: str, category: str, key_name: str, value: str):
        encrypted = self.encryptor.encrypt(value)
        self.dao.insert(user_id, category, key_name, encrypted)

    def retrieve(self, user_id: str, category: Optional[str] = None) -> List[str]:
        rows = self.dao.select(user_id, category)
        result = []
        for key_name, enc_val in rows:
            try:
                plain = self.encryptor.decrypt(enc_val)
                result.append(f"{key_name}: {plain}")
            except Exception as e:
                print(f"[WARN] Decrypt failed for {key_name}: {e}")
        return result
