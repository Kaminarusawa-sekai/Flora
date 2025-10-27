# config.py
import os

# DashScope (Qwen)
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "192.168.10.33")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "8888"))
MYSQL_USER = os.getenv("MYSQL_USER", "test_read")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "123@123")
MYSQL_MAX_CONNECTIONS = 20  # 连接池大小

# Chroma
CHROMA_PERSIST_DIR = "./chroma_storage"

# 学习策略
MIN_RESULT_ROWS = 1          # 至少返回 1 行才学习
MAX_SQL_LENGTH = 1000        # 防止超长 SQL
ALLOWED_TABLES = None        # 可设为白名单，如 ["sales", "users"]