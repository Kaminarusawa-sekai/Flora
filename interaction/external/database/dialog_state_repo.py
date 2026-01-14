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
        
         # 处理列表字段的默认值
        if 'pending_tasks' not in data:
            data['pending_tasks'] = []
        if 'recent_tasks' not in data:
            data['recent_tasks'] = []
        if 'missing_required_slots' not in data:
            data['missing_required_slots'] = []
        
        # 处理布尔字段的默认值
        for bool_field in ['is_in_idle_mode', 'requires_clarification', 'waiting_for_confirmation']:
            if bool_field not in data:
                data[bool_field] = False
        
        # 处理 Optional 字段的默认值
        for optional_field in ['current_intent', 'active_task_execution', 
                               'last_mentioned_task_id', 'clarification_context', 'clarification_message',
                               'confirmation_action', 'confirmation_payload', 'current_request_id']:
            if optional_field not in data:
                data[optional_field] = None
        
        # 特殊处理 active_task_draft（包含枚举和嵌套对象）
        if 'active_task_draft' in data and data['active_task_draft']:
            draft_data = data['active_task_draft']
            
            # 确保 status 是枚举值
            if 'status' in draft_data:
                
                draft_data['status'] = TaskDraftStatus(draft_data['status'])
            
            # 处理 slots 中的 SlotValueDTO 对象
            if 'slots' in draft_data and draft_data['slots']:
                for slot_name, slot_value in draft_data['slots'].items():
                    # 确保 source 是枚举值
                    if isinstance(slot_value, dict) and 'source' in slot_value:
                        slot_value['source'] = SlotSource(slot_value['source'])
                        draft_data['slots'][slot_name] = SlotValueDTO(**slot_value)
            
            # 处理 schedule 对象
            if 'schedule' in draft_data and draft_data['schedule']:
                draft_data['schedule'] = ScheduleDTO(**draft_data['schedule'])
            
            # 处理其他默认值
            if 'is_dynamic_schema' not in draft_data:
                draft_data['is_dynamic_schema'] = True
            if 'completeness_score' not in draft_data:
                draft_data['completeness_score'] = 0.0
            if 'original_utterances' not in draft_data:
                draft_data['original_utterances'] = []
            if 'missing_slots' not in draft_data:
                draft_data['missing_slots'] = []
            if 'invalid_slots' not in draft_data:
                draft_data['invalid_slots'] = []
            if 'user_id' not in draft_data:
                draft_data['user_id'] = ''
            
            # 将 draft_data 转换为 TaskDraftDTO 对象
            data['active_task_draft'] = TaskDraftDTO(**draft_data)
        else:
            data['active_task_draft'] = None
        
        # 确保 last_updated 是 datetime
        if 'last_updated' in data:
            # 如果是字符串，转换为 datetime
            if isinstance(data['last_updated'], str):
                data['last_updated'] = datetime.fromisoformat(data['last_updated'].replace('Z', '+00:00'))
            # 如果是时间戳，转换为 datetime
            elif isinstance(data['last_updated'], (int, float)):
                data['last_updated'] = datetime.fromtimestamp(data['last_updated'], timezone.utc)
        else:
            data['last_updated'] = datetime.now(timezone.utc)
        
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
            cursor.execute('''
                SELECT state_json, last_updated
                FROM dialog_states
                ORDER BY last_updated DESC
            ''')
            rows = cursor.fetchall()
            
            sessions: List[DialogStateDTO] = []
            for row in rows:
                state = self._deserialize_state(row[0])
                if state.user_id == user_id:
                    sessions.append(state)
            
            return sessions
        except Exception as e:
            logger.error(f"Failed to get sessions by user id {user_id}: {e}")
            return []
        finally:
            self.pool.return_connection(conn)