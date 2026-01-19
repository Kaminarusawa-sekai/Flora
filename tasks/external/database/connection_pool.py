"""MySQL连接池管理"""
import pymysql
from pymysql.cursors import DictCursor

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class BaseConnectionPool(ABC):
    """
    通用数据库连接池基类
    """
    
    def __init__(self, config: Dict[str, Any]=None):
        """
        初始化连接池
        
        Args:
            config: 数据库配置
        """
        self.config = config
    
    @abstractmethod
    def get_connection(self):
        """
        获取数据库连接
        
        Returns:
            数据库连接对象
        """
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        执行查询操作
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            list: 查询结果
        """
        pass
    
    @abstractmethod
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行更新操作
        
        Args:
            query: SQL语句
            params: 查询参数
            
        Returns:
            int: 受影响的行数
        """
        pass


class MySQLConnectionPool(BaseConnectionPool):
    """
    MySQL连接池管理类
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化连接池
        
        Args:
            config: 数据库配置
        """
        super().__init__(config)
        self.max_reconnect_attempts = self.config.get('max_reconnect_attempts', 3) if config else 3
    
    def get_connection(self):
        """
        获取数据库连接
        
        Returns:
            pymysql.connections.Connection: 数据库连接对象
        """

        if self.config==None:
            from config import MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_CHARSET, MYSQL_MAX_CONNECTIONS
            self.config = {
                'host': MYSQL_HOST,
                'port': MYSQL_PORT,
                'user': MYSQL_USER,
                'password': MYSQL_PASSWORD,
                'charset': MYSQL_CHARSET,
                'max_connections': MYSQL_MAX_CONNECTIONS
            }

        return pymysql.connect(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 3306),
            user=self.config['user'],
            password=self.config['password'],
            database=self.config.get('database', ''),
            charset=self.config.get('charset', 'utf8mb4'),
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=10,
            read_timeout=30,
            write_timeout=30,
            # 添加自动重连配置
            max_allowed_packet=1024 * 1024 * 16
        )
    
    def _is_connection_healthy(self, conn):
        """
        检查连接是否健康
        
        Args:
            conn: 数据库连接对象
            
        Returns:
            bool: 连接是否健康
        """
        try:
            # 执行简单的ping命令检查连接
            conn.ping(reconnect=False)
            return True
        except (pymysql.Error, AttributeError):
            return False
    
    def _get_healthy_connection(self):
        """
        获取健康的数据库连接
        
        Returns:
            pymysql.connections.Connection: 健康的数据库连接对象
        """
        attempt = 0
        while attempt < self.max_reconnect_attempts:
            try:
                conn = self.get_connection()
                if self._is_connection_healthy(conn):
                    return conn
                conn.close()
            except pymysql.Error as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
            attempt += 1
        
        # 最后一次尝试，不捕获异常
        conn = self.get_connection()
        if self._is_connection_healthy(conn):
            return conn
        conn.close()
        raise pymysql.Error(f"Failed to get healthy connection after {self.max_reconnect_attempts} attempts")
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        执行查询操作
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            list: 查询结果
        """
        with self._get_healthy_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or {})
                return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行更新操作
        
        Args:
            query: SQL语句
            params: 查询参数
            
        Returns:
            int: 受影响的行数
        """
        with self._get_healthy_connection() as conn:
            with conn.cursor() as cursor:
                result = cursor.execute(query, params or {})
                conn.commit()
                return result


class PostgreSQLConnectionPool(BaseConnectionPool):
    """
    PostgreSQL连接池管理类
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
                - sslmode: SSL模式
        """
        super().__init__(config)
        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
        except ImportError:
            raise ImportError("psycopg2 is required for PostgreSQL support. Install it with 'pip install psycopg2-binary'")
    
    def get_connection(self):
        """
        获取数据库连接
        
        Returns:
            psycopg2.connection: 数据库连接对象
        """
        if self.config==None:
            from config import POSTGRESQL_HOST, POSTGRESQL_PORT, POSTGRESQL_USER, POSTGRESQL_PASSWORD
            self.config = {
                'host': POSTGRESQL_HOST,
                'port': POSTGRESQL_PORT,
                'user': POSTGRESQL_USER,
                'password': POSTGRESQL_PASSWORD,
            }

        return self.psycopg2.connect(
            host=self.config.get('host', 'localhost'),
            port=self.config.get('port', 5432),
            user=self.config['user'],
            password=self.config['password'],
            database=self.config['database'],
            sslmode=self.config.get('sslmode', 'prefer')
        )
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
        """
        执行查询操作
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            list: 查询结果
        """
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=self.extras.RealDictCursor) as cursor:
                cursor.execute(query, params or {})
                return cursor.fetchall()
    
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
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
                return cursor.rowcount


class SQLServerConnectionPool(BaseConnectionPool):
    """
    SQL Server连接池管理类
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
                - driver: ODBC驱动名称
        """
        super().__init__(config)
        try:
            import pyodbc
            self.pyodbc = pyodbc
        except ImportError:
            raise ImportError("pyodbc is required for SQL Server support. Install it with 'pip install pyodbc'")
    
    def get_connection(self):
        """
        获取数据库连接
        
        Returns:
            pyodbc.Connection: 数据库连接对象
        """
        if self.config==None:
            from config import SQLSERVER_HOST, SQLSERVER_PORT, SQLSERVER_USER, SQLSERVER_PASSWORD, SQLSERVER_DRIVER
            self.config = {
                'host': SQLSERVER_HOST,
                'port': SQLSERVER_PORT,
                'user': SQLSERVER_USER,
                'password': SQLSERVER_PASSWORD,
                'driver': SQLSERVER_DRIVER
            }
        connection_string = (
            f"DRIVER={self.config.get('driver', '{ODBC Driver 17 for SQL Server}')};"
            f"SERVER={self.config['host']},{self.config.get('port', 1433)};"
            f"DATABASE={self.config['database']};"
            f"UID={self.config['user']};"
            f"PWD={self.config['password']}"
        )
        return self.pyodbc.connect(connection_string)
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
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
                if params:
                    # 将字典参数转换为元组格式
                    param_values = tuple(params.values())
                    cursor.execute(query, param_values)
                else:
                    cursor.execute(query)
                columns = [column[0] for column in cursor.description]
                results = cursor.fetchall()
                # 将结果转换为字典列表格式
                return [dict(zip(columns, row)) for row in results]
    
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
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
                if params:
                    # 将字典参数转换为元组格式
                    param_values = tuple(params.values())
                    cursor.execute(query, param_values)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount


class OracleConnectionPool(BaseConnectionPool):
    """
    Oracle连接池管理类
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
                - service_name: 服务名
                - sid: 数据库SID
        """
        super().__init__(config)
        try:
            import cx_Oracle
            self.cx_Oracle = cx_Oracle
        except ImportError:
            raise ImportError("cx_Oracle is required for Oracle support. Install it with 'pip install cx_Oracle'")
    
    def get_connection(self):
        """
        获取数据库连接
        
        Returns:
            cx_Oracle.Connection: 数据库连接对象
        """
        if self.config==None:
            from config import ORACLE_HOST, ORACLE_PORT, ORACLE_USER, ORACLE_PASSWORD, ORACLE_SID
            self.config = {
                'host': ORACLE_HOST,
                'port': ORACLE_PORT,
                'user': ORACLE_USER,
                'password': ORACLE_PASSWORD,
                'sid': ORACLE_SID
            }
        dsn = self.cx_Oracle.makedsn(
            self.config['host'],
            self.config.get('port', 1521),
            service_name=self.config.get('service_name'),
            sid=self.config.get('sid')
        )
        return self.cx_Oracle.connect(
            user=self.config['user'],
            password=self.config['password'],
            dsn=dsn
        )
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict]:
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
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                columns = [col[0] for col in cursor.description]
                results = cursor.fetchall()
                # 将结果转换为字典列表格式
                return [dict(zip(columns, row)) for row in results]
    
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
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
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                conn.commit()
                return cursor.rowcount


class ConnectionPoolFactory:
    """
    连接池工厂类，根据数据库类型创建相应的连接池实例
    """
    
    @staticmethod
    def create_pool(db_type: str, config: Optional[Dict[str, Any]] = None) -> BaseConnectionPool:
        """
        根据数据库类型创建相应的连接池实例
        
        Args:
            db_type: 数据库类型 ('mysql', 'postgresql', 'sqlserver', 'oracle')
            config: 数据库配置
            
        Returns:
            BaseConnectionPool 实例
        """
        db_type = db_type.lower()
        
        if db_type == 'mysql':
            return MySQLConnectionPool(config)
        elif db_type == 'postgresql':
            return PostgreSQLConnectionPool(config)
        elif db_type == 'sqlserver':
            return SQLServerConnectionPool(config)
        elif db_type == 'oracle':
            return OracleConnectionPool(config)
        else:
            raise ValueError(f"Unsupported database type: {db_type}")