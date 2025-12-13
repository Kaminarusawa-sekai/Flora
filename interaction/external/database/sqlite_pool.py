import sqlite3
from typing import Optional, List
from queue import Queue
import threading

class SQLiteConnectionPool:
    def __init__(self, db_path: str, max_connections: int = 5):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = Queue(maxsize=max_connections)
        self.lock = threading.Lock()
        self._initialize_pool()
    
    def _initialize_pool(self):
        for _ in range(self.max_connections):
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            self.connections.put(conn)
    
    def get_connection(self) -> sqlite3.Connection:
        return self.connections.get()
    
    def return_connection(self, conn: sqlite3.Connection):
        self.connections.put(conn)
    
    def close_all(self):
        while not self.connections.empty():
            conn = self.connections.get()
            conn.close()
    
    def __del__(self):
        self.close_all()