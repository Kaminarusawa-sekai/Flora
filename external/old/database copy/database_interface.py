"""数据库适配器抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple


class DatabaseInterface(ABC):
    """
    数据库适配器抽象接口，定义所有数据库适配器必须实现的方法
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """
        建立数据库连接
        
        Returns:
            bool: 连接是否成功
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        断开数据库连接
        
        Returns:
            bool: 断开是否成功
        """
        pass
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行查询操作
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        pass
    
    @abstractmethod
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行更新操作（插入、更新、删除）
        
        Args:
            query: SQL语句
            params: 查询参数
            
        Returns:
            int: 受影响的行数
        """
        pass
    
    @abstractmethod
    def begin_transaction(self) -> bool:
        """
        开始事务
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def commit_transaction(self) -> bool:
        """
        提交事务
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def rollback_transaction(self) -> bool:
        """
        回滚事务
        
        Returns:
            bool: 是否成功
        """
        pass
    
    @abstractmethod
    def get_connection_status(self) -> bool:
        """
        获取连接状态
        
        Returns:
            bool: 是否已连接
        """
        pass
