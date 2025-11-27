# neo4j_registry.py（最终优化版 - 使用 MarketingTreeDemo1 节点）

from neo4j import GraphDatabase, Driver
from typing import List, Dict, Any, Optional, Set
import logging
import threading
from thespian.actors import ActorAddress

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

        # 运行时 Actor 地址映射
        self._actor_refs: Dict[str, ActorAddress] = {}
        
        # 缓存元数据：key 是 code（作为 agent_id）
        self._agent_meta_cache: Optional[Dict[str, Dict]] = None
        self._parent_map: Dict[str, str] = {}          # code -> parent_code
        self._children_map: Dict[str, List[str]] = {}  # parent_code -> [child_code, ...]
        
        self._lock = threading.RLock()
        self._initialized = True

    @classmethod
    def get_instance(
        cls,
        uri: str = None,
        user: str = None,
        password: str = None
    ) -> "AgentRegistry":
        if cls._instance is not None:
            return cls._instance
        return cls(uri, user, password)

    def close(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass

    # ==============================
    # 【Actor 引用管理 - 支持角色区分】
    # ==============================
    def register_actor_ref(self, agent_id: str,  actor_ref: ActorAddress,role: str="business",):
        """
        注册指定角色的 Actor 引用。
        常见 role: "business", "data"
        """
        with self._lock:
            if agent_id not in self._actor_refs:
                self._actor_refs[agent_id] = {}
            if role in self._actor_refs[agent_id]:
                logger.warning(f"Actor ref for {agent_id}[{role}] is being overwritten.")
            self._actor_refs[agent_id][role] = actor_ref
            logger.debug(f"Registered {role} actor ref for {agent_id}: {actor_ref}")

    def get_actor_ref(self, agent_id: str, role: str = "business") -> Optional[ActorAddress]:
        """默认 role="business" 保持向后兼容（如果你需要）"""
        with self._lock:
            return self._actor_refs.get(agent_id, {}).get(role)

    def get_actor_refs_by_ids(self, agent_ids: List[str], role: str = "business") -> Dict[str, Optional[ActorAddress]]:
        with self._lock:
            return {
                aid: self._actor_refs.get(aid, {}).get(role)
                for aid in agent_ids
            }

    def has_actor_ref(self, agent_id: str, role: str = "business") -> bool:
        with self._lock:
            return agent_id in self._actor_refs and role in self._actor_refs[agent_id]

    # 可选：获取某个 agent 的所有角色映射
    def get_all_actor_refs(self, agent_id: str) -> Dict[str, ActorAddress]:
        with self._lock:
            return self._actor_refs.get(agent_id, {}).copy()
    # ==============================
    # 【缓存加载与元数据】
    # ==============================
    def _rebuild_maps(self, agents: Dict[str, Dict]):
        self._parent_map.clear()
        self._children_map.clear()
        for code, meta in agents.items():
            parent_code = meta.get("parent_code")
            if parent_code:
                self._parent_map[code] = parent_code
                self._children_map.setdefault(parent_code, []).append(code)

    def ensure_meta_loaded(self):
        with self._lock:
            if self._agent_meta_cache is None:
                raw_agents = self.load_all_agents()
                self._agent_meta_cache = raw_agents
                self._rebuild_maps(raw_agents)

    def get_agent_meta(self, agent_id: str) -> Optional[Dict]:
        self.ensure_meta_loaded()
        with self._lock:
            return self._agent_meta_cache.get(agent_id)

    def get_all_agent_ids(self) -> Set[str]:
        self.ensure_meta_loaded()
        with self._lock:
            return set(self._agent_meta_cache.keys())

    # ==============================
    # 【关系导航】
    # ==============================
    def get_parent(self, agent_id: str) -> Optional[str]:
        self.ensure_meta_loaded()
        with self._lock:
            return self._parent_map.get(agent_id)

    def get_children(self, agent_id: str) -> List[str]:
        self.ensure_meta_loaded()
        with self._lock:
            return list(self._children_map.get(agent_id, []))

    def get_siblings(self, agent_id: str) -> List[str]:
        parent = self.get_parent(agent_id)
        if not parent:
            return []
        children = self.get_children(parent)
        return [cid for cid in children if cid != agent_id]

    # ==============================
    # 【Actor 地址按关系获取】
    # ==============================
    def get_parent_actor(self, agent_id: str) -> Optional[ActorAddress]:
        parent_id = self.get_parent(agent_id)
        return self.get_actor_ref(parent_id) if parent_id else None

    def get_children_actors(self, agent_id: str) -> Dict[str, Optional[ActorAddress]]:
        child_ids = self.get_children(agent_id)
        return self.get_actor_refs_by_ids(child_ids)

    def get_siblings_actors(self, agent_id: str) -> Dict[str, Optional[ActorAddress]]:
        sibling_ids = self.get_siblings(agent_id)
        return self.get_actor_refs_by_ids(sibling_ids)

    # ==============================
    # 【Neo4j 数据操作 - 使用 MarketingTreeDemo1】
    # ==============================
    def load_all_agents(self) -> Dict[str, Dict]:
        with self.driver.session() as session:
            return session.execute_read(self._load_all_agents_tx)

    @staticmethod
    def _load_all_agents_tx(tx):
        res = tx.run("""
            MATCH (n:MarketingTreeDemo2)
            OPTIONAL MATCH (n)-[:CHILD_OF]->(parent:MarketingTreeDemo2)  
            OPTIONAL MATCH (child:MarketingTreeDemo2)-[:CHILD_OF]->(n)   
            RETURN 
                n.code AS code,
                n.name AS name,
                n.businessId AS businessId,
                n.strength AS strength,
                n.seq AS seq,
                n.capability AS capability,
                n.datascope AS datascope,
                n.database AS database,
                n.dify AS dify,
                parent.code AS parent_code,
                count(child) = 0 AS is_leaf
            ORDER BY n.code
        """)
        agents = {}
        for record in res:
            code = record["code"]
            agents[code] = {
                "agent_id": record["businessId"],  # 统一用 code 作为 agent_id
                "code": code,
                "name": record["name"],
                "businessId": record["businessId"],
                "strength": record["strength"],
                "seq": record["seq"],
                "capability": record["capability"] or '',
                "datascope": record["datascope"] or '',
                "database": (record["database"] or ''),
                "is_leaf": record["is_leaf"],  # 新增字段：是否为叶子节点
                "dify": record["dify"] or '',  # 新增字段：Dify Workflow 代码
                "parent_code": record["parent_code"]
            }
        return agents

    def register_agent(
        self,
        agent_id: str,  # 实际是 code
        capabilities: List[str],
        data_scope: Dict[str, Any],
        is_leaf: bool = False,
        parent_agent_id: Optional[str] = None  # parent code
    ):
        with self.driver.session() as session:
            session.write_transaction(
                self._register_agent_tx,
                agent_id, capabilities, data_scope, is_leaf, parent_agent_id
            )
        with self._lock:
            self._agent_meta_cache = None
            self._parent_map.clear()
            self._children_map.clear()

    @staticmethod
    def _register_agent_tx(tx, agent_id, capabilities, data_scope, is_leaf, parent_agent_id):
        # 确保节点存在（根据 code）
        tx.run("""
            MERGE (n:MarketingTreeDemo2 {code: $code})
            SET 
                n.capabilities = $capabilities,
                n.data_scope = $data_scope,
                n.is_leaf = $is_leaf,
                n.updated_at = datetime()
            """,
            code=agent_id,
            capabilities=capabilities,
            data_scope=data_scope,
            is_leaf=is_leaf
        )
        if parent_agent_id:
            tx.run("""
                MATCH (child:MarketingTreeDemo2 {code: $child_code})
                MATCH (parent:MarketingTreeDemo2 {code: $parent_code})
                MERGE (child)-[:CHILD_OF]->(parent)
                """,
                child_code=agent_id,
                parent_code=parent_agent_id
            )

    def has_agent(self, agent_id: str) -> bool:
        self.ensure_meta_loaded()
        with self._lock:
            return agent_id in self._agent_meta_cache

    # ==============================
    # 【兼容：通过 businessId 查节点】
    # ==============================
    def get_agent_id_by_user(self, x_tenant_id: str, user_id: str) -> Optional[str]:
        return "private_domain"