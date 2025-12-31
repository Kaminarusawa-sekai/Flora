# interaction/external/database/dialog_state_repo.py

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
import json
import logging
from sqlite3 import Connection
from pydantic import BaseModel

from common.response_state import DialogStateDTO
from common.task_draft import TaskDraftDTO, TaskDraftStatus, SlotValueDTO, ScheduleDTO
from common.base import SlotSource
from .sqlite_pool import SQLiteConnectionPool

# 配置日志
logger = logging.getLogger(__name__)


class DialogStateRepository:
    def __init__(self, pool: Optional[SQLiteConnectionPool] = None):
        self.pool = pool or SQLiteConnectionPool(db_path="dialogs.db")
        # print(self.pool.db_path)
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
        return state.model_dump_json(exclude_none=True)  # Pydantic v2, 排除None值以减少存储大小

    def _deserialize_state(self, json_str: str) -> DialogStateDTO:
        data = json.loads(json_str)
        
        # 处理必填字段的默认值，确保兼容旧数据
        if 'user_id' not in data:
            data['user_id'] = ''
        if 'name' not in data:
            data['name'] = ''
        if 'description' not in data:
            data['description'] = ''
        
        return DialogStateDTO.model_validate(data)

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
        except Exception as e:
            logger.error(f"Failed to save dialog state for session {state.session_id}: {e}")
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
        except Exception as e:
            logger.error(f"Failed to get dialog state for session {session_id}: {e}")
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
        except Exception as e:
            logger.error(f"Failed to delete dialog state for session {session_id}: {e}")
            return False
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
        except Exception as e:
            logger.error(f"Failed to find expired sessions: {e}")
            return []
        finally:
            self.pool.return_connection(conn)

    def get_all_session_ids(self) -> List[str]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT session_id FROM dialog_states')
            return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to get all session ids: {e}")
            return []
        finally:
            self.pool.return_connection(conn)

    def get_sessions_by_user_id(self, user_id: str) -> List[DialogStateDTO]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT state_json FROM dialog_states')
            rows = cursor.fetchall()
            
            user_sessions = []
            for row in rows:
                state = self._deserialize_state(row[0])
                if state.user_id == user_id:
                    user_sessions.append(state)
            
            return user_sessions
        except Exception as e:
            logger.error(f"Failed to get sessions by user id {user_id}: {e}")
            return []
        finally:
            self.pool.return_connection(conn)