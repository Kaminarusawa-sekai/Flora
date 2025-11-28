"""Neo4j客户端封装"""
from neo4j import GraphDatabase, Driver
from typing import Any, List, Dict, Optional
from config import NEO4J_URI , NEO4J_USER, NEO4J_PASSWORD


class Neo4jClient:
    """
    Neo4j客户端封装，提供基础的Neo4j操作方法
    """
    
    def __init__(self, uri: str=NEO4J_URI, user: str=NEO4J_USER, password: str=NEO4J_PASSWORD):
        """
        初始化Neo4j客户端
        
        Args:
            config: Neo4j配置
                - uri: Neo4j连接URI
                - user: 用户名
                - password: 密码
        """
    
        self.uri = uri
        self.user = user
        self.password = password
        self.driver: Optional[Driver] = None
    
    def connect(self) -> None:
        """
        建立Neo4j连接
        """
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
    
    def disconnect(self) -> None:
        """
        断开Neo4j连接
        """
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def execute_query(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行Cypher查询
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果
        """
        if not self.driver:
            self.connect()
        
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    
    def execute_write(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        执行写操作
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            Any: 查询结果
        """
        if not self.driver:
            self.connect()
        
        with self.driver.session() as session:
            result = session.write_transaction(lambda tx: tx.run(query, parameters or {}).single())
            return result.data() if result else None
    
    def execute_read(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> Any:
        """
        执行读操作
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            
        Returns:
            Any: 查询结果
        """
        if not self.driver:
            self.connect()
        
        with self.driver.session() as session:
            result = session.read_transaction(lambda tx: tx.run(query, parameters or {}).single())
            return result.data() if result else None
