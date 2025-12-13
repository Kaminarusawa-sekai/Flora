from typing import List, Optional, Dict, Any
from sqlite3 import Connection
from interaction.common.dialog import DialogTurn
from .sqlite_pool import SQLiteConnectionPool

class DialogRepository:
    def __init__(self, pool: Optional[SQLiteConnectionPool] = None):
        self.pool = pool or SQLiteConnectionPool(db_path="dialogs.db")
        self._create_table()
    
    def _create_table(self):
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dialog_turns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    utterance TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    enhanced_utterance TEXT
                )
            ''')
            conn.commit()
        finally:
            self.pool.return_connection(conn)
    
    def save_turn(self, turn: DialogTurn) -> int:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO dialog_turns (role, utterance, timestamp, enhanced_utterance)
                VALUES (?, ?, ?, ?)
            ''', (turn.role, turn.utterance, turn.timestamp, turn.enhanced_utterance))
            conn.commit()
            return cursor.lastrowid
        finally:
            self.pool.return_connection(conn)
    
    def get_turn_by_id(self, turn_id: int) -> Optional[DialogTurn]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT role, utterance, timestamp, enhanced_utterance
                FROM dialog_turns
                WHERE id = ?
            ''', (turn_id,))
            row = cursor.fetchone()
            if row:
                return DialogTurn(
                    role=row['role'],
                    utterance=row['utterance'],
                    timestamp=row['timestamp'],
                    enhanced_utterance=row['enhanced_utterance']
                )
            return None
        finally:
            self.pool.return_connection(conn)
    
    def get_all_turns(self) -> List[DialogTurn]:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT role, utterance, timestamp, enhanced_utterance
                FROM dialog_turns
                ORDER BY timestamp
            ''')
            rows = cursor.fetchall()
            return [
                DialogTurn(
                    role=row['role'],
                    utterance=row['utterance'],
                    timestamp=row['timestamp'],
                    enhanced_utterance=row['enhanced_utterance']
                )
                for row in rows
            ]
        finally:
            self.pool.return_connection(conn)
    
    def update_turn(self, turn_id: int, enhanced_utterance: str) -> bool:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE dialog_turns
                SET enhanced_utterance = ?
                WHERE id = ?
            ''', (enhanced_utterance, turn_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            self.pool.return_connection(conn)
    
    def delete_turn(self, turn_id: int) -> bool:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM dialog_turns
                WHERE id = ?
            ''', (turn_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            self.pool.return_connection(conn)
    
    def delete_all_turns(self) -> bool:
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM dialog_turns')
            conn.commit()
            return cursor.rowcount > 0
        finally:
            self.pool.return_connection(conn)
    
    def delete_old_turns(self, keep: int) -> bool:
        """
        删除旧的对话轮次，保留最近的keep个轮次
        
        Args:
            keep: 要保留的最近轮次数
            
        Returns:
            删除是否成功
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            # 先获取要保留的最小ID
            cursor.execute('''
                SELECT MIN(id) FROM (
                    SELECT id FROM dialog_turns
                    ORDER BY timestamp DESC
                    LIMIT ?
                ) AS recent_turns
            ''', (keep,))
            min_id = cursor.fetchone()[0]
            
            if min_id:
                # 删除小于该ID的所有轮次
                cursor.execute('DELETE FROM dialog_turns WHERE id < ?', (min_id,))
                conn.commit()
                return cursor.rowcount > 0
            return False
        finally:
            self.pool.return_connection(conn)
    
    def get_oldest_turns(self, n: int) -> List[Dict[str, Any]]:
        """
        获取最早的n个对话轮次
        
        Args:
            n: 要获取的轮次数
            
        Returns:
            对话轮次列表
        """
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, role, utterance, timestamp, enhanced_utterance
                FROM dialog_turns
                ORDER BY timestamp ASC
                LIMIT ?
            ''', (n,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            self.pool.return_connection(conn)
    
    def delete_turns_by_ids(self, turn_ids: List[int]) -> bool:
        """
        根据ID列表删除对话轮次
        
        Args:
            turn_ids: 要删除的轮次ID列表
            
        Returns:
            删除是否成功
        """
        if not turn_ids:
            return False
            
        conn = self.pool.get_connection()
        try:
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(turn_ids))
            cursor.execute(f'DELETE FROM dialog_turns WHERE id IN ({placeholders})', turn_ids)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            self.pool.return_connection(conn)