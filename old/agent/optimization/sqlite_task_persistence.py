# persistence_adapters.py

import sqlite3
import json
import threading
from pathlib import Path
from typing import Dict, Optional
from contextlib import contextmanager

from agent.optimization.optimization_task import OptimizationTask


class SqlitePersistence:
    def __init__(self, db_path: str, agent_id: str):
        self.db_path = Path(db_path)
        self.agent_id = agent_id
        self._local = threading.local()  # 每线程/进程独立连接（Thespian 多进程下天然隔离）
        self._init_db()

    @contextmanager
    def _get_conn(self):
        """获取数据库连接（支持 with 语句）"""
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # Thespian 可能在不同线程初始化，但实际每个 Actor 独占
                isolation_level=None      # 自动提交
            )
            self._local.conn.row_factory = sqlite3.Row
        try:
            yield self._local.conn
        except Exception:
            self._local.conn.rollback()
            raise

    def _init_db(self):
        """初始化数据库表"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS optimization_tasks (
                    agent_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    capability TEXT NOT NULL,
                    test_context TEXT NOT NULL,  -- JSON string
                    interval_seconds INTEGER NOT NULL,
                    enabled BOOLEAN NOT NULL,
                    paused BOOLEAN NOT NULL,
                    PRIMARY KEY (agent_id, task_id)
                )
            """)
            conn.commit()

    def save_tasks(self, tasks: Dict[str, OptimizationTask]):
        """保存所有任务（全量覆盖当前 agent_id 的任务）"""
        with self._get_conn() as conn:
            # 先删除当前 agent 的所有任务
            conn.execute("DELETE FROM optimization_tasks WHERE agent_id = ?", (self.agent_id,))
            
            # 再插入新任务
            for task in tasks.values():
                conn.execute("""
                    INSERT INTO optimization_tasks
                    (agent_id, task_id, capability, test_context, interval_seconds, enabled, paused)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.agent_id,
                    task.task_id,
                    task.capability,
                    json.dumps(task.test_context, ensure_ascii=False),
                    task.interval_seconds,
                    int(task.enabled),   # bool -> int (SQLite 不支持 bool)
                    int(task.paused)
                ))
            conn.commit()

    def load_tasks(self) -> Dict[str, OptimizationTask]:
        """加载当前 agent_id 的所有任务"""
        with self._get_conn() as conn:
            rows = conn.execute("""
                SELECT task_id, capability, test_context, interval_seconds, enabled, paused
                FROM optimization_tasks
                WHERE agent_id = ?
            """, (self.agent_id,)).fetchall()

            tasks = {}
            for row in rows:
                try:
                    task = OptimizationTask(
                        task_id=row["task_id"],
                        capability=row["capability"],
                        test_context=json.loads(row["test_context"]),
                        interval_seconds=row["interval_seconds"],
                        enabled=bool(row["enabled"]),
                        paused=bool(row["paused"])
                    )
                    tasks[task.task_id] = task
                except Exception as e:
                    # 跳过损坏条目，记录日志
                    print(f"Warning: Failed to load task {row['task_id']}: {e}")
                    continue
            return tasks