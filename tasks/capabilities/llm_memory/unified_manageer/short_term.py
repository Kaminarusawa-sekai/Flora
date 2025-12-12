# memory/short_term.py
from typing import List, Dict
from tasks.external.memory_store.stm_dao import STMRecordDAO

class ShortTermMemory:
    def __init__(self, db_path: str = "memory.db", max_history: int = 10):
        self.dao = STMRecordDAO(db_path)
        self.max_history = max_history

    def add_message(self, user_id: str, role: str, content: str):
        self.dao.add_message(user_id, role, content)

    def get_history(self, user_id: str, n: int = None) -> List[Dict[str, str]]:
        n = n or self.max_history
        return self.dao.get_recent_messages(user_id, limit=n)

    def format_history(self, user_id: str, n: int = 6) -> str:
        history = self.get_history(user_id, n)
        return "\n".join([f"{m['role']}: {m['content']}" for m in history])

    def clear_user(self, user_id: str):
        self.dao.clear_user_history(user_id)

    def cleanup(self, max_age_seconds: int = 86400 * 7):
        """定期调用清理旧记录"""
        self.dao.cleanup_old_records(max_age_seconds)