import sqlite3
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from .task_models import TaskDefinition, TaskInstance, TaskStatus, TaskTriggerType

class TaskRepository:
    def __init__(self, db_path: str = "tasks.sqlite"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 创建任务定义表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_definitions (
                    task_def_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    trigger_type TEXT NOT NULL,
                    trigger_args TEXT,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL
                )
            ''')
            
            # 创建任务实例表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS task_instances (
                    instance_id TEXT PRIMARY KEY,
                    task_def_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    result TEXT,
                    error TEXT,
                    FOREIGN KEY (task_def_id) REFERENCES task_definitions (task_def_id)
                )
            ''')
            
            conn.commit()
    
    def create_definition(self, task_def_id: str, user_id: str, content: str, 
                         trigger_type: TaskTriggerType, trigger_args: Optional[Dict[str, Any]] = None) -> TaskDefinition:
        """创建任务定义"""
        now = datetime.now()
        trigger_args_json = json.dumps(trigger_args) if trigger_args else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_definitions 
                (task_def_id, user_id, content, trigger_type, trigger_args, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_def_id, user_id, content, trigger_type.value, 
                trigger_args_json, TaskStatus.ACTIVE.value, now, now
            ))
            conn.commit()
        
        return TaskDefinition(
            task_def_id=task_def_id,
            user_id=user_id,
            content=content,
            trigger_type=trigger_type,
            trigger_args=trigger_args,
            status=TaskStatus.ACTIVE,
            created_at=now,
            updated_at=now
        )
    
    def get_definition(self, task_def_id: str) -> Optional[TaskDefinition]:
        """获取任务定义"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_def_id, user_id, content, trigger_type, trigger_args, status, created_at, updated_at
                FROM task_definitions
                WHERE task_def_id = ?
            ''', (task_def_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
        
        task_def_id, user_id, content, trigger_type, trigger_args_json, status, created_at, updated_at = row
        trigger_args = json.loads(trigger_args_json) if trigger_args_json else None
        
        return TaskDefinition(
            task_def_id=task_def_id,
            user_id=user_id,
            content=content,
            trigger_type=TaskTriggerType(trigger_type),
            trigger_args=trigger_args,
            status=TaskStatus(status),
            created_at=datetime.fromisoformat(created_at),
            updated_at=datetime.fromisoformat(updated_at)
        )
    
    def update_def_status(self, task_def_id: str, status: TaskStatus):
        """更新任务定义状态"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE task_definitions
                SET status = ?, updated_at = ?
                WHERE task_def_id = ?
            ''', (status.value, datetime.now(), task_def_id))
            conn.commit()
    
    def record_instance_start(self, instance_id: str, task_def_id: str, content: str) -> TaskInstance:
        """记录任务实例开始"""
        now = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO task_instances 
                (instance_id, task_def_id, content, status, created_at, started_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                instance_id, task_def_id, content, TaskStatus.RUNNING.value, now, now
            ))
            conn.commit()
        
        return TaskInstance(
            instance_id=instance_id,
            task_def_id=task_def_id,
            content=content,
            status=TaskStatus.RUNNING,
            created_at=now,
            started_at=now
        )
    
    def record_instance_complete(self, instance_id: str, result: Optional[Dict[str, Any]] = None, 
                               error: Optional[str] = None):
        """记录任务实例完成"""
        completed_at = datetime.now()
        status = TaskStatus.COMPLETED if not error else TaskStatus.CANCELLED
        result_json = json.dumps(result) if result else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE task_instances
                SET status = ?, completed_at = ?, result = ?, error = ?
                WHERE instance_id = ?
            ''', (status.value, completed_at, result_json, error, instance_id))
            conn.commit()
    
    def get_definitions_by_user(self, user_id: str) -> List[TaskDefinition]:
        """获取用户的所有任务定义"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT task_def_id, user_id, content, trigger_type, trigger_args, status, created_at, updated_at
                FROM task_definitions
                WHERE user_id = ?
            ''', (user_id,))
            
            rows = cursor.fetchall()
        
        definitions = []
        for row in rows:
            task_def_id, user_id, content, trigger_type, trigger_args_json, status, created_at, updated_at = row
            trigger_args = json.loads(trigger_args_json) if trigger_args_json else None
            
            definitions.append(TaskDefinition(
                task_def_id=task_def_id,
                user_id=user_id,
                content=content,
                trigger_type=TaskTriggerType(trigger_type),
                trigger_args=trigger_args,
                status=TaskStatus(status),
                created_at=datetime.fromisoformat(created_at),
                updated_at=datetime.fromisoformat(updated_at)
            ))
        
        return definitions
    
    def get_instances_by_definition(self, task_def_id: str) -> List[TaskInstance]:
        """获取任务定义的所有实例"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT instance_id, task_def_id, content, status, created_at, started_at, completed_at, result, error
                FROM task_instances
                WHERE task_def_id = ?
                ORDER BY created_at DESC
            ''', (task_def_id,))
            
            rows = cursor.fetchall()
        
        instances = []
        for row in rows:
            instance_id, task_def_id, content, status, created_at, started_at, completed_at, result_json, error = row
            result = json.loads(result_json) if result_json else None
            
            instances.append(TaskInstance(
                instance_id=instance_id,
                task_def_id=task_def_id,
                content=content,
                status=TaskStatus(status),
                created_at=datetime.fromisoformat(created_at),
                started_at=datetime.fromisoformat(started_at) if started_at else None,
                completed_at=datetime.fromisoformat(completed_at) if completed_at else None,
                result=result,
                error=error
            ))
        
        return instances