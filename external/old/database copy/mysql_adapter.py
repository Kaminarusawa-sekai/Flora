"""MySQL数据库适配器"""
import pymysql
import pymysql.cursors
from typing import Dict, Any, List, Optional
from .database_interface import DatabaseInterface
from ..adapter_base import AdapterBase


class MySQLAdapter(AdapterBase, DatabaseInterface):
    """
    MySQL数据库适配器，用于连接和操作MySQL数据库
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化MySQL适配器
        
        Args:
            config: 数据库配置
                - host: 数据库主机地址
                - port: 数据库端口
                - user: 用户名
                - password: 密码
                - database: 数据库名
                - charset: 字符集，默认为'utf8mb4'
                - cursorclass: 游标类，默认为DictCursor
        """
        super().__init__(config)
        self.connection = None
        self.cursor = None
    
    def initialize(self) -> bool:
        """
        初始化适配器，建立数据库连接
        
        Returns:
            bool: 初始化是否成功
        """
        return self.connect()
    
    def connect(self) -> bool:
        """
        建立MySQL数据库连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 从配置中获取连接参数
            host = self.get_config_value('host', 'localhost')
            port = self.get_config_value('port', 3306)
            user = self.get_config_value('user')
            password = self.get_config_value('password')
            database = self.get_config_value('database')
            charset = self.get_config_value('charset', 'utf8mb4')
            
            # 创建连接
            self.connection = pymysql.connect(
                host=host,
                port=port,
                user=user,
                password=password,
                database=database,
                charset=charset,
                cursorclass=pymysql.cursors.DictCursor
            )
            
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"MySQL连接失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        断开数据库连接
        
        Returns:
            bool: 断开是否成功
        """
        try:
            if self.cursor:
                self.cursor.close()
                self.cursor = None
            
            if self.connection:
                self.connection.close()
                self.connection = None
                
            self.is_initialized = False
            return True
        except Exception as e:
            print(f"MySQL断开连接失败: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        if not self.get_connection_status():
            if not self.connect():
                raise ConnectionError("数据库连接失败")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or {})
                return cursor.fetchall()
        except Exception as e:
            print(f"MySQL查询失败: {e}")
            raise
    
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行更新操作
        
        Args:
            query: SQL语句
            params: 查询参数
            
        Returns:
            int: 受影响的行数
        """
        if not self.get_connection_status():
            if not self.connect():
                raise ConnectionError("数据库连接失败")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(query, params or {})
                self.connection.commit()
                return cursor.rowcount
        except Exception as e:
            print(f"MySQL更新失败: {e}")
            self.connection.rollback()
            raise
    
    def begin_transaction(self) -> bool:
        """
        开始事务
        
        Returns:
            bool: 是否成功
        """
        if not self.get_connection_status():
            if not self.connect():
                return False
        
        try:
            self.connection.begin()
            return True
        except Exception as e:
            print(f"MySQL开始事务失败: {e}")
            return False
    
    def commit_transaction(self) -> bool:
        """
        提交事务
        
        Returns:
            bool: 是否成功
        """
        if not self.get_connection_status():
            return False
        
        try:
            self.connection.commit()
            return True
        except Exception as e:
            print(f"MySQL提交事务失败: {e}")
            return False
    
    def rollback_transaction(self) -> bool:
        """
        回滚事务
        
        Returns:
            bool: 是否成功
        """
        if not self.get_connection_status():
            return False
        
        try:
            self.connection.rollback()
            return True
        except Exception as e:
            print(f"MySQL回滚事务失败: {e}")
            return False
    
    def get_connection_status(self) -> bool:
        """
        获取连接状态
        
        Returns:
            bool: 是否已连接
        """
        if not self.connection:
            return False
        
        try:
            self.connection.ping(reconnect=False)
            return True
        except:
            return False
    
    def close(self) -> None:
        """
        关闭适配器，释放资源
        """
        self.disconnect()
