# mysql_pool.py
import pymysql
from dbutils.pooled_db import PooledDB
from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_MAX_CONNECTIONS


class MySQLPool:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.pool = PooledDB(
                creator=pymysql,
                maxconnections=MYSQL_MAX_CONNECTIONS,
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                charset='utf8mb4',
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor
            )
        return cls._instance

    # mysql_pool.py（或你的连接池模块）
    def get_connection(self, database: str = None):
        # ✅ 不再切换数据库！直接返回连接
        return self.pool.connection()

# 全局单例
mysql_pool = MySQLPool()