# interaction/external/database/dialog_state_repo.py

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
from sqlite3 import Connection
from pydantic import BaseModel

from interaction.common.response_state import DialogStateDTO
from .sqlite_pool import SQLiteConnectionPool


class DialogStateRepository:
    def __init__(self, pool: Optional[SQLiteConnectionPool] = None):
        self.pool = pool or SQLiteConnectionPool(db_path="dialogs.db")
        self._create_table()

    def _create_table(self):
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dialog_states (
                    session_id TEXT PRIMARY KEY,
                    state_json TEXT NOT NULL,
                    last_updated REAL NOT NULL
                )
            ''')
            conn.commit()
        finally:
            self.pool.return_connection(conn)

    def _serialize_state(self, state: DialogStateDTO) -> str:
        return state.model_dump_json()  # Pydantic v2

    def _deserialize_state(self, json_str: str) -> DialogStateDTO:
        data = json.loads(json_str)
        # 确保 last_updated 是 datetime（Pydantic 通常能自动处理）
        return DialogStateDTO(**data)

    def save_dialog_state(self, state: DialogStateDTO) -> bool:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            state_json = self._serialize_state(state)
            timestamp = state.last_updated.timestamp()
            cursor.execute('''
                INSERT OR REPLACE INTO dialog_states (session_id, state_json, last_updated)
                VALUES (?, ?, ?)
            ''', (state.session_id, state_json, timestamp))
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            self.pool.return_connection(conn)

    def get_dialog_state(self, session_id: str) -> Optional[DialogStateDTO]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT state_json FROM dialog_states WHERE session_id = ?
            ''', (session_id,))
            row = cursor.fetchone()
            if row:
                return self._deserialize_state(row[0])
            return None
        finally:
            self.pool.return_connection(conn)

    def update_dialog_state(self, state: DialogStateDTO) -> bool:
        # 在 SQLite 中，INSERT OR REPLACE 已经覆盖更新
        return self.save_dialog_state(state)

    def delete_dialog_state(self, session_id: str) -> bool:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM dialog_states WHERE session_id = ?', (session_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            self.pool.return_connection(conn)

    def find_expired_sessions(self, cutoff: datetime) -> List[str]:
        """
        查找 last_updated 早于 cutoff 的会话 ID
        """
        cutoff_ts = cutoff.timestamp()
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT session_id FROM dialog_states
                WHERE last_updated < ?
            ''', (cutoff_ts,))
            rows = cursor.fetchall()
            return [row[0] for row in rows]
        finally:
            self.pool.return_connection(conn)

    def get_all_session_ids(self) -> List[str]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT session_id FROM dialog_states')
            return [row[0] for row in cursor.fetchall()]
        finally:
            self.pool.return_connection(conn)