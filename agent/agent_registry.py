# neo4j_registry.py（增强版：支持全量加载）

from neo4j import GraphDatabase, Driver
from typing import List, Dict, Any, Optional, Tuple
import logging
from typing import List, Dict, Any, Optional, Tuple
import threading

logger = logging.getLogger(__name__)


class AgentRegistry:

    _instance = None
    _init_lock = threading.Lock()


    def __new__(cls, uri: str = None, user: str = None, password: str = None):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    if uri is None or user is None or password is None:
                        raise ValueError(
                            "AgentRegistry singleton requires 'uri', 'user', and 'password' on first instantiation."
                        )
                    cls._instance = super(AgentRegistry, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    def __init__(self, uri: str, user: str, password: str):

        if self._initialized:
            return
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    @classmethod
    def get_instance(
        cls,
        uri: str = None,
        user: str = None,
        password: str = None
    ) -> "AgentRegistry":
        """
        获取全局单例实例。

        - 首次调用必须提供 uri, user, password。
        - 后续调用可不传参。
        """
        if cls._instance is not None:
            return cls._instance
        # 触发 __new__ 和 __init__
        return cls(uri, user, password)

    def close(self):
        """关闭 Neo4j 驱动连接（谨慎使用，通常在应用退出时调用）"""
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()

    def __del__(self):
        # 可选：自动清理，但不保证及时执行
        try:
            self.close()
        except Exception:
            pass


    # ==============================
    # 【新增】从 Neo4j 全量加载智能体结构（含父子关系）
    # ==============================
    def load_all_agents(self) -> Dict[str, Dict]:
        """
        从 Neo4j 中加载所有智能体，并返回一个字典：
        {
          "agent_id": {
            "agent_id": str,
            "capabilities": List[str],
            "data_scope": Dict,
            "is_leaf": bool,
            "parent": Optional[str]   # 父 agent_id（如果有）
          },
          ...
        }
        """
        with self.driver.session() as session:
            result = session.read_transaction(self._load_all_agents_tx)
            return result

    @staticmethod
    def _load_all_agents_tx(tx):
        # 查询所有 Agent 节点及其父节点（如果有）
        res = tx.run("""
            MATCH (a:Agent)
            OPTIONAL MATCH (a)-[:CHILD_OF]->(p:Agent)
            RETURN a.agent_id AS agent_id,
                   a.capabilities AS capabilities,
                   a.data_scope AS data_scope,
                   a.is_leaf AS is_leaf,
                   p.agent_id AS parent_id
            ORDER BY a.agent_id
        """)
        
        agents = {}
        for record in res:
            agent_id = record["agent_id"]
            agents[agent_id] = {
                "agent_id": agent_id,
                "capabilities": record["capabilities"] or [],
                "data_scope": record["data_scope"] or {},
                "is_leaf": bool(record["is_leaf"]),
                "parent": record["parent_id"]  # 可能为 None
            }
        return agents

    # ==============================
    # 原有 API（保持不变）
    # ==============================
    def register_agent(
        self,
        agent_id: str,
        capabilities: List[str],
        data_scope: Dict[str, Any],
        is_leaf: bool = False,
        parent_agent_id: Optional[str] = None
    ):
        with self.driver.session() as session:
            session.write_transaction(
                self._register_agent_tx,
                agent_id, capabilities, data_scope, is_leaf, parent_agent_id
            )

    @staticmethod
    def _register_agent_tx(tx, agent_id, capabilities, data_scope, is_leaf, parent_agent_id):
        tx.run("""
            MERGE (a:Agent {agent_id: $agent_id})
            SET a.capabilities = $capabilities,
                a.data_scope = $data_scope,
                a.is_leaf = $is_leaf,
                a.updated_at = datetime()
            """,
            agent_id=agent_id,
            capabilities=capabilities,
            data_scope=data_scope,
            is_leaf=is_leaf
        )
        if parent_agent_id:
            tx.run("""
                MATCH (child:Agent {agent_id: $child_id})
                MATCH (parent:Agent {agent_id: $parent_id})
                MERGE (child)-[:CHILD_OF]->(parent)
                """,
                child_id=agent_id,
                parent_id=parent_agent_id
            )

    def get_agent_by_id(self, agent_id: str) -> Optional[Dict]:
        with self.driver.session() as session:
            result = session.read_transaction(self._get_agent_by_id_tx, agent_id)
            return result

    @staticmethod
    def _get_agent_by_id_tx(tx, agent_id):
        res = tx.run("""
            MATCH (a:Agent {agent_id: $agent_id})
            RETURN a.agent_id AS agent_id,
                   a.capabilities AS capabilities,
                   a.data_scope AS data_scope,
                   a.is_leaf AS is_leaf
            """, agent_id=agent_id)
        record = res.single()
        return record.data() if record else None

    def get_direct_children(self, parent_agent_id: str) -> List[Dict]:
        with self.driver.session() as session:
            return session.read_transaction(self._get_direct_children_tx, parent_agent_id)

    @staticmethod
    def _get_direct_children_tx(tx, parent_agent_id):
        res = tx.run("""
            MATCH (child:Agent)-[:CHILD_OF]->(:Agent {agent_id: $parent_id})
            RETURN child.agent_id AS agent_id,
                   child.capabilities AS capabilities,
                   child.data_scope AS data_scope,
                   child.is_leaf AS is_leaf
            ORDER BY child.agent_id
            """, parent_id=parent_agent_id)
        return [record.data() for record in res]

    def find_direct_child_by_capability(
        self,
        parent_agent_id: str,
        capability: str,
        context: Dict[str, Any]
    ) -> Optional[Dict]:
        children = self.get_direct_children(parent_agent_id)
        for child in children:
            if (capability in child["capabilities"] and
                self._matches_data_scope(child["data_scope"], context)):
                return child
        return None

    @staticmethod
    def _matches_data_scope(data_scope: Dict, context: Dict) -> bool:
        return all(context.get(k) == v for k, v in data_scope.items())
    

    def get_agent_id_by_user(self, x_tenant_id:str,user_id: str) -> Optional[str]:
       return "root_router"  # TODO:实现用户到根智能体的映射逻辑
    

    def has_agent(self,agent_id: str) -> bool:
        return True
        with self.driver.session() as session:
            result = session.read_transaction(AgentRegistry._has_agent_tx, agent_id)
            return result