"""Neo4j数据库适配器"""
from neo4j import GraphDatabase, basic_auth
from typing import Dict, Any, List, Optional, Tuple
from .database_interface import DatabaseInterface
from ..adapter_base import AdapterBase


class Neo4jAdapter(AdapterBase, DatabaseInterface):
    """
    Neo4j数据库适配器，用于连接和操作Neo4j图数据库
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Neo4j适配器
        
        Args:
            config: 数据库配置
                - uri: Neo4j连接URI
                - user: 用户名
                - password: 密码
                - database: 数据库名，默认为'neo4j'
        """
        super().__init__(config)
        self.driver = None
        self.current_database = self.get_config_value('database', 'neo4j')
    
    def initialize(self) -> bool:
        """
        初始化适配器，建立数据库连接
        
        Returns:
            bool: 初始化是否成功
        """
        return self.connect()
    
    def connect(self) -> bool:
        """
        建立Neo4j数据库连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 从配置中获取连接参数
            uri = self.get_config_value('uri', 'neo4j://localhost:7687')
            user = self.get_config_value('user')
            password = self.get_config_value('password')
            
            # 创建连接驱动
            self.driver = GraphDatabase.driver(
                uri,
                auth=basic_auth(user, password)
            )
            
            # 测试连接
            with self.driver.session(database=self.current_database) as session:
                session.run("RETURN 1")
            
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"Neo4j连接失败: {e}")
            return False
    
    def disconnect(self) -> bool:
        """
        断开数据库连接
        
        Returns:
            bool: 断开是否成功
        """
        try:
            if self.driver:
                self.driver.close()
                self.driver = None
                
            self.is_initialized = False
            return True
        except Exception as e:
            print(f"Neo4j断开连接失败: {e}")
            return False
    
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行Cypher查询
        
        Args:
            query: Cypher查询语句
            params: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        if not self.get_connection_status():
            if not self.connect():
                raise ConnectionError("数据库连接失败")
        
        try:
            results = []
            with self.driver.session(database=self.current_database) as session:
                result = session.run(query, params or {})
                for record in result:
                    results.append(dict(record))
            return results
        except Exception as e:
            print(f"Neo4j查询失败: {e}")
            raise
    
    def execute_update(self, query: str, params: Optional[Dict[str, Any]] = None) -> int:
        """
        执行更新操作（创建、更新、删除节点或关系）
        
        Args:
            query: Cypher语句
            params: 查询参数
            
        Returns:
            int: 受影响的记录数
        """
        if not self.get_connection_status():
            if not self.connect():
                raise ConnectionError("数据库连接失败")
        
        try:
            with self.driver.session(database=self.current_database) as session:
                result = session.run(query, params or {})
                return result.consume().counters.properties_set
        except Exception as e:
            print(f"Neo4j更新失败: {e}")
            raise
    
    def begin_transaction(self) -> bool:
        """
        开始事务
        
        Returns:
            bool: 是否成功
        """
        # Neo4j通过session管理事务，这里返回True表示支持事务
        return self.get_connection_status()
    
    def commit_transaction(self) -> bool:
        """
        提交事务
        
        Returns:
            bool: 是否成功
        """
        # Neo4j的session.run默认是自动提交的
        return self.get_connection_status()
    
    def rollback_transaction(self) -> bool:
        """
        回滚事务
        
        Returns:
            bool: 是否成功
        """
        # 在Neo4j中，显式事务需要使用session.begin_transaction()
        return self.get_connection_status()
    
    def get_connection_status(self) -> bool:
        """
        获取连接状态
        
        Returns:
            bool: 是否已连接
        """
        if not self.driver:
            return False
        
        try:
            with self.driver.session(database=self.current_database) as session:
                session.run("RETURN 1")
            return True
        except:
            return False
    
    def close(self) -> None:
        """
        关闭适配器，释放资源
        """
        self.disconnect()
    
    def execute_transaction(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        在显式事务中执行查询
        
        Args:
            query: Cypher查询语句
            params: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        if not self.get_connection_status():
            if not self.connect():
                raise ConnectionError("数据库连接失败")
        
        try:
            results = []
            with self.driver.session(database=self.current_database) as session:
                tx = session.begin_transaction()
                try:
                    result = tx.run(query, params or {})
                    for record in result:
                        results.append(dict(record))
                    tx.commit()
                except Exception:
                    tx.rollback()
                    raise
            return results
        except Exception as e:
            print(f"Neo4j事务执行失败: {e}")
            raise
