"""基于MySQL的业务数据管理实现"""
import pymysql
import pymysql.cursors
from typing import List, Dict, Any, Optional
from .data_interface import BusinessDataInterface


class MySQLBusinessData(BusinessDataInterface):
    """
    使用MySQL实现的业务数据管理器，基于连接池
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化MySQL连接池
        
        Args:
            config: MySQL连接配置
        """
        self.config = config
        self.pool = self._create_pool(config)
    
    def _create_pool(self, config: Dict[str, Any]):
        """
        创建MySQL连接池
        
        Args:
            config: 连接配置
            
        Returns:
            pymysql连接池
        """
        # 提取连接池配置
        pool_config = {
            'host': config.get('host', 'localhost'),
            'port': config.get('port', 3306),
            'user': config.get('user'),
            'password': config.get('password'),
            'db': config.get('database'),
            'charset': config.get('charset', 'utf8mb4'),
            'cursorclass': pymysql.cursors.DictCursor,
            'maxconnections': config.get('max_connections', 10)
        }
        
        # 创建连接池
        from pymysqlpool import ConnectionPool
        return ConnectionPool(**pool_config)
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数（命名参数）
            
        Returns:
            查询结果列表
        """
        with self.pool.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params or {})
                result = cursor.fetchall()
            return result
    
    def close(self) -> None:
        """
        关闭连接池
        """
        if hasattr(self, 'pool') and self.pool:
            self.pool.close()
    
    def begin_transaction(self) -> Any:
        """
        开始事务
        
        Returns:
            事务对象，包含连接和游标
        """
        conn = self.pool.get_connection()
        conn.begin()
        cursor = conn.cursor()
        return {
            'connection': conn,
            'cursor': cursor
        }
    
    def commit_transaction(self, transaction: Dict[str, Any]) -> None:
        """
        提交事务
        
        Args:
            transaction: 事务对象
        """
        conn = transaction.get('connection')
        if conn:
            conn.commit()
            # 关闭游标
            cursor = transaction.get('cursor')
            if cursor:
                cursor.close()
            # 归还连接到池中
            conn.close()
    
    def rollback_transaction(self, transaction: Dict[str, Any]) -> None:
        """
        回滚事务
        
        Args:
            transaction: 事务对象
        """
        conn = transaction.get('connection')
        if conn:
            conn.rollback()
            # 关闭游标
            cursor = transaction.get('cursor')
            if cursor:
                cursor.close()
            # 归还连接到池中
            conn.close()
