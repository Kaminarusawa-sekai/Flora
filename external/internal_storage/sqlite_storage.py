"""基于SQLite的内部持久化存储实现"""
import sqlite3
import json
from typing import Dict, Any, Optional
from .storage_interface import InternalStorageInterface


class SQLiteInternalStorage(InternalStorageInterface):
    """
    使用SQLite实现的内部持久化存储管理器
    """
    
    def __init__(self, db_path: str):
        """
        初始化SQLite连接
        
        Args:
            db_path: SQLite数据库文件路径
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._init_tables()
    
    def _init_tables(self) -> None:
        """
        初始化数据库表结构
        """
        cursor = self.conn.cursor()
        
        # 创建任务状态表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS task_states (
            task_id TEXT PRIMARY KEY,
            state_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建自学习模型表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_models (
            model_id TEXT PRIMARY KEY,
            model_data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # 创建更新触发器
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_task_state_time
        AFTER UPDATE ON task_states
        FOR EACH ROW
        BEGIN
            UPDATE task_states SET updated_at = CURRENT_TIMESTAMP WHERE task_id = NEW.task_id;
        END
        ''')
        
        cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_model_time
        AFTER UPDATE ON learning_models
        FOR EACH ROW
        BEGIN
            UPDATE learning_models SET updated_at = CURRENT_TIMESTAMP WHERE model_id = NEW.model_id;
        END
        ''')
        
        self.conn.commit()
    
    def save_task_state(self, task_id: str, state_data: Dict[str, Any]) -> bool:
        """
        保存任务状态
        
        Args:
            task_id: 任务唯一标识符
            state_data: 任务状态数据
            
        Returns:
            是否保存成功
        """
        try:
            json_data = json.dumps(state_data, ensure_ascii=False)
            cursor = self.conn.cursor()
            
            # 使用INSERT OR REPLACE进行插入或更新
            cursor.execute(
                '''INSERT OR REPLACE INTO task_states (task_id, state_data)
                VALUES (?, ?)''',
                (task_id, json_data)
            )
            
            self.conn.commit()
            return True
        except Exception:
            return False
    
    def load_task_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        加载任务状态
        
        Args:
            task_id: 任务唯一标识符
            
        Returns:
            任务状态数据，如果不存在返回None
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''SELECT state_data FROM task_states WHERE task_id = ?''',
                (task_id,)
            )
            result = cursor.fetchone()
            
            if result:
                return json.loads(result[0])
            return None
        except Exception:
            return None
    
    def save_learning_model(self, model_id: str, model_data: Dict[str, Any]) -> bool:
        """
        保存自学习模型
        
        Args:
            model_id: 模型唯一标识符
            model_data: 模型数据
            
        Returns:
            是否保存成功
        """
        try:
            json_data = json.dumps(model_data, ensure_ascii=False)
            cursor = self.conn.cursor()
            
            # 使用INSERT OR REPLACE进行插入或更新
            cursor.execute(
                '''INSERT OR REPLACE INTO learning_models (model_id, model_data)
                VALUES (?, ?)''',
                (model_id, json_data)
            )
            
            self.conn.commit()
            return True
        except Exception:
            return False
    
    def close(self) -> None:
        """
        关闭SQLite连接
        """
        if self.conn:
            self.conn.close()
    
    def delete_task_state(self, task_id: str) -> bool:
        """
        删除任务状态
        
        Args:
            task_id: 任务唯一标识符
            
        Returns:
            是否删除成功
        """
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                '''DELETE FROM task_states WHERE task_id = ?''',
                (task_id,)
            )
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
