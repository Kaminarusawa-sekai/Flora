# memory/base_sqlite.py
import sqlite3
import json
import os
from datetime import datetime
from typing import List, Dict, Any

DB_DIR = "db"
os.makedirs(DB_DIR, exist_ok=True)

class SQLiteMemoryBase:
    def __init__(self, db_name: str, table_name: str, schema: str):
        self.db_path = os.path.join(DB_DIR, db_name)
        self.table_name = table_name
        self.init_db(schema)

    def init_db(self, schema: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(schema)

    def insert(self, data: Dict[str, Any]):
        keys = ', '.join(data.keys())
        placeholders = ', '.join(['?'] * len(data))
        values = tuple(data.values())
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"INSERT INTO {self.table_name} ({keys}) VALUES ({placeholders})", values)

    def query(self, where_clause: str = "", params: tuple = ()) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.execute(f"SELECT * FROM {self.table_name} {where_clause}", params)
            return [dict(row) for row in cur.fetchall()]

    def delete_all(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"DELETE FROM {self.table_name}")



