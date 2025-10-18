# neo4j_registry.py（最终增强版）

from neo4j import GraphDatabase, Driver
from typing import List, Dict, Any, Optional, Tuple
import logging
import threading
from thespian.actors import ActorAddress  # ← 关键：引入 ActorAddress

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

        # === 新增：运行时 Actor 地址映射 ===
        self._actor_refs: Dict[str, ActorAddress] = {}
        self._agent_meta_cache: Optional[Dict[str, Dict]] = None  # 缓存 load_all_agents()
        self._lock = threading.RLock()  # 读写锁，保证线程安全

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
    # 【运行时】注册 Actor 实例地址
    # ==============================
    def register_actor_ref(self, agent_id: str, actor_ref: ActorAddress):
        """在启动 Actor 后调用，绑定 agent_id → ActorAddress"""
        with self._lock:
            if agent_id in self._actor_refs:
                logger.warning(f"Actor ref for {agent_id} is being overwritten.")
            self._actor_refs[agent_id] = actor_ref
            logger.debug(f"Registered actor ref for {agent_id}: {actor_ref}")

    def get_actor_ref(self, agent_id: str) -> Optional[ActorAddress]:
        """根据 agent_id 获取运行时 Actor 地址"""
        with self._lock:
            return self._actor_refs.get(agent_id)

    def has_actor_ref(self, agent_id: str) -> bool:
        with self._lock:
            return agent_id in self._actor_refs

    # ==============================
    # 【元数据】缓存全量 agent 信息（避免频繁查 Neo4j）
    # ==============================
    def ensure_meta_loaded(self):
        """懒加载 + 缓存元数据"""
        with self._lock:
            if self._agent_meta_cache is None:
                self._agent_meta_cache = self.load_all_agents()

    def get_agent_meta(self, agent_id: str) -> Optional[Dict]:
        self.ensure_meta_loaded()
        with self._lock:
            return self._agent_meta_cache.get(agent_id)

    def get_all_agent_meta(self) -> Dict[str, Dict]:
        self.ensure_meta_loaded()
        with self._lock:
            return dict(self._agent_meta_cache)  # 返回副本避免外部修改

    # ==============================
    # 【路由】根据 capability + context 找到目标 agent_id
    # ==============================
    def find_agent_by_capability(
        self,
        capability: str,
        context: Dict[str, Any],
        parent_agent_id: Optional[str] = None
    ) -> Optional[str]:
        """
        路由逻辑：
        - 如果指定了 parent_agent_id，则只在其 direct children 中查找
        - 否则全局查找（适用于根调用）
        """
        self.ensure_meta_loaded()
        candidates = []

        with self._lock:
            all_meta = self._agent_meta_cache

        if parent_agent_id:
            # 只查 direct children of parent
            children = self.get_direct_children(parent_agent_id)
            candidate_ids = [c["agent_id"] for c in children]
            candidate_metas = {cid: all_meta[cid] for cid in candidate_ids if cid in all_meta}
        else:
            # 全局查找
            candidate_metas = all_meta

        for aid, meta in candidate_metas.items():
            if capability in meta.get("capabilities", []) and self._matches_data_scope(meta.get("data_scope", {}), context):
                candidates.append(aid)

        if not candidates:
            return None
        if len(candidates) > 1:
            logger.warning(f"Multiple agents match capability={capability}, context={context}. Picking first: {candidates[0]}")
        return candidates[0]

    # ==============================
    # 【原有 Neo4j 方法】保持不变（略作优化）
    # ==============================
    def load_all_agents(self) -> Dict[str, Dict]:
        with self.driver.session() as session:
            return session.execute_read(self._load_all_agents_tx)

    @staticmethod
    def _load_all_agents_tx(tx):
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
                "parent": record["parent_id"]
            }
        return agents

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
        # 清除缓存，下次自动重载
        with self._lock:
            self._agent_meta_cache = None

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

    def get_direct_children(self, parent_agent_id: str) -> List[Dict]:
        with self.driver.session() as session:
            return session.execute_read(self._get_direct_children_tx, parent_agent_id)

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

    @staticmethod
    def _matches_data_scope(data_scope: Dict, context: Dict) -> bool:
        return all(context.get(k) == v for k, v in data_scope.items())

    # ==============================
    # 【其他方法】保持兼容
    # ==============================
    def get_agent_by_id(self, business_id: int) -> Optional[Dict]:
        with self.driver.session() as session:
            return session.execute_read(self._get_by_business_id_tx, business_id)

    @staticmethod
    def _get_by_business_id_tx(tx, business_id: int):
        query = """
            MATCH (n:MarketingTreeDemo1 {businessId: $business_id})
            RETURN n.code AS code,
                n.name AS name,
                n.businessId AS businessId,
                n.strength AS strength,
                n.seq AS seq
            """
        record = tx.run(query, business_id=business_id).single()
        return record.data() if record else None

    def get_agent_id_by_user(self, x_tenant_id: str, user_id: str) -> Optional[str]:
        # TODO: 实现用户到根智能体的映射
        return 17  # 示例

    def has_agent(self, agent_id: str) -> bool:
        self.ensure_meta_loaded()
        with self._lock:
            return agent_id in self._agent_meta_cache