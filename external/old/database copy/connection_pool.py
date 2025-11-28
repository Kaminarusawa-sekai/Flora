"""MySQL连接池管理"""
import pymysql
from pymysql.cursors import DictCursor
from typing import Dict, Any, Optional


class MySQLConnectionPool:
    """
    MySQL连接池管理类
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化连接池
        
        Args:
            config: 数据库配置
                - host: 数据库主机地址
                - port: 数据库端口
                - user: 用户名
                - password: 密码
                - database: 数据库名
                - charset: 字符集，默认为'utf8mb4'
        """
        self.config = config
        self.pool = None
    
    def get_connection(self):
        """
        获取数据库连接
        
        Returns:
            pymysql.connections.Connection: 数据库连接对象
        """
        return pymysql.connect(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 3306),
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            charset=self.config.get('charset', 'utf8mb4'),
            cursorclass=DictCursor
        )
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        执行查询操作
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            list: 查询结果
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or {})
                return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        执行更新操作
        
        Args:
            query: SQL语句
            params: 查询参数
            
        Returns:
            int: 受影响的行数
        """
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                result = cursor.execute(query, params or {})
                conn.commit()
                return result
