"""基于Neo4j的Agent树形结构管理实现"""
from typing import Dict, List, Any
import logging
from neo4j import GraphDatabase
from .structure_interface import AgentStructureInterface


class Neo4JAgentStructure(AgentStructureInterface):
    """
    使用Neo4j实现的Agent树形结构管理器
    实现单例模式确保全局只创建一个数据库连接
    """
    _instances = {}  # 单例实例字典，支持不同配置的单例

    def __new__(cls, uri: str, user: str, password: str):
        """
        实现单例模式
        
        Args:
            uri: Neo4j数据库URI
            user: 用户名
            password: 密码
        
        Returns:
            Neo4JAgentStructure: 单例实例
        """
        # 使用配置信息作为单例的键
        key = (uri, user, password)
        if key not in cls._instances:
            cls._instances[key] = super(Neo4JAgentStructure, cls).__new__(cls)
            # 初始化数据库连接
            cls._instances[key].driver = GraphDatabase.driver(uri, auth=(user, password))
        return cls._instances[key]
    
    def get_agent_relationship(self, agent_id: str) -> Dict[str, Any]:
        """
        获取Agent的父子关系
        
        Args:
            agent_id: Agent唯一标识符
            
        Returns:
            包含父Agent和子Agent信息的字典
        """
        with self.driver.session() as session:
            result = session.read_transaction(self._get_relationship_tx, agent_id)
            return result
    
    def _get_relationship_tx(self, tx, agent_id: str) -> Dict[str, Any]:
        """事务函数：查询Agent关系"""
        # 查询父节点
        parent_query = """
        MATCH (parent)-[:HAS_CHILD]->(child {id: $agent_id})
        RETURN parent.id as parent_id, parent.meta as parent_meta
        LIMIT 1
        """
        parent_result = tx.run(parent_query, agent_id=agent_id).single()
        
        # 查询子节点
        children_query = """
        MATCH (parent {id: $agent_id})-[:HAS_CHILD]->(child)
        RETURN child.id as child_id, child.meta as child_meta
        """
        children_result = tx.run(children_query, agent_id=agent_id).data()
        
        return {
            'agent_id': agent_id,
            'parent': parent_result.data() if parent_result else None,
            'children': [{k: v for k, v in record.items()} for record in children_result]
        }
    
    def load_all_agents(self) -> List[Dict[str, Any]]:
        """
        加载所有Agent节点
        
        Returns:
            Agent节点信息列表
        """
        with self.driver.session() as session:
            result = session.read_transaction(self._load_all_agents_tx)
            return result
    
    def _load_all_agents_tx(self, tx) -> List[Dict[str, Any]]:
        """事务函数：加载所有Agent"""
        query = """
        MATCH (a)
        WHERE a:Agent
        RETURN a.id as agent_id, a.meta as meta
        """
        result = tx.run(query).data()
        return [{k: v for k, v in record.items()} for record in result]
    
    def close(self) -> None:
        """
        关闭Neo4j连接
        """
        if hasattr(self, 'driver') and self.driver is not None:
            self.driver.close()
            logging.info("Neo4j driver connection closed")
    
    def add_agent_relationship(self, parent_id: str, child_id: str, relationship_type: str = 'HAS_CHILD') -> bool:
        """
        添加Agent间的父子关系
        
        Args:
            parent_id: 父Agent ID
            child_id: 子Agent ID
            relationship_type: 关系类型
            
        Returns:
            是否添加成功
        """
        try:
            with self.driver.session() as session:
                session.write_transaction(
                    self._add_relationship_tx, 
                    parent_id, 
                    child_id, 
                    relationship_type
                )
            return True
        except Exception:
            return False
    
    def _add_relationship_tx(self, tx, parent_id: str, child_id: str, relationship_type: str):
        """事务函数：添加关系"""
        query = """
        MATCH (parent {id: $parent_id})
        MATCH (child {id: $child_id})
        MERGE (parent)-[:HAS_CHILD]->(child)
        """
        tx.run(query, parent_id=parent_id, child_id=child_id)
    
    def get_agent_by_id(self, agent_id: str) -> Dict[str, Any]:
        """
        获取指定Agent的信息
        
        Args:
            agent_id: Agent唯一标识符
            
        Returns:
            Agent信息字典
        """
        with self.driver.session() as session:
            result = session.read_transaction(self._get_agent_by_id_tx, agent_id)
            return result if result else None
    
    def _get_agent_by_id_tx(self, tx, agent_id: str) -> Dict[str, Any]:
        """事务函数：查询单个Agent"""
        query = """
        MATCH (a:Agent {id: $agent_id})
        RETURN a.id as agent_id, a.meta as meta
        """
        result = tx.run(query, agent_id=agent_id).single()
        return dict(result) if result else None
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        删除指定Agent及其所有关系
        
        Args:
            agent_id: 要删除的Agent ID
            
        Returns:
            是否删除成功
        """
        try:
            with self.driver.session() as session:
                session.write_transaction(self._remove_agent_tx, agent_id)
            return True
        except Exception:
            return False
    
    def _remove_agent_tx(self, tx, agent_id: str):
        """事务函数：删除Agent"""
        # 先删除所有与该Agent相关的关系
        query_remove_relationships = """
        MATCH (a {id: $agent_id})-[r]-()
        DELETE r
        """
        tx.run(query_remove_relationships, agent_id=agent_id)
        
        # 再删除Agent节点
        query_remove_node = """
        MATCH (a {id: $agent_id})
        DELETE a
        """
        tx.run(query_remove_node, agent_id=agent_id)
