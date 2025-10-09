# database.py
import sqlite3
from config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS execution_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT NOT NULL,
            run_id TEXT UNIQUE NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            prompt TEXT NOT NULL,
            output TEXT,
            metrics TEXT NOT NULL,
            feedback TEXT,
            logs TEXT,
            outputs TEXT,
            metadata TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS optimization_episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            episode_id TEXT UNIQUE NOT NULL,
            task_id TEXT NOT NULL,
            state_before TEXT NOT NULL,
            action_taken TEXT NOT NULL,
            state_after TEXT,
            reward REAL,
            applied_by TEXT,
            timestamp TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    conn.commit()
    conn.close()

def save_execution_result(result: dict):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO execution_history 
        (task_id, run_id, timestamp, status, prompt, output, metrics, feedback, logs, outputs, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        result["task_id"], result["run_id"], result["timestamp"],
        result["status"], result["prompt"], result.get("output"),
        str(result["metrics"]), str(result.get("feedback")),
        str(result.get("logs")), str(result.get("outputs")),
        str(result.get("metadata"))
    ))
    conn.commit()
    conn.close()