# actor_manager.py

import threading
from typing import Dict, Type, Any, Optional, Callable, List
from agent.agent_actor import AgentActor
from agent.agent_registry import AgentRegistry
import logging

logger = logging.getLogger(__name__)


class ActorManager:
    """
    多租户 Actor 管理器，元数据从 Neo4j 动态加载。

    - 每个 (tenant_id, agent_id) 对应唯一 Actor 实例
    - 元数据（capabilities, data_scope, is_leaf）来自 AgentRegistry
    - 支持启动时预加载所有智能体（可选）
    - 线程安全
    """

    _instance = None
    _init_lock = threading.Lock()  # 用于控制单例初始化的线程安全

    def __new__(cls, registry: AgentRegistry = None, actor_class: Type[AgentActor] = None):
        if cls._instance is None:
            with cls._init_lock:
                # 双重检查锁定（Double-checked locking）
                if cls._instance is None:
                    if registry is None or actor_class is None:
                        raise ValueError(
                            "ActorManager singleton requires 'registry' and 'actor_class' on first instantiation."
                        )
                    cls._instance = super(ActorManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, registry: AgentRegistry, actor_class: Type[AgentActor]):
        """
        初始化 ActorManager。

        :param registry: 已连接的 AgentRegistry 实例
        :param actor_class: 要创建的 Actor 类（如 AgentActor）
        """

        # 防止重复初始化
        if self._initialized:
            return
        
        self.registry = registry
        self.actor_class = actor_class

        # 结构: _actors[tenant_id][agent_id] = AgentActor 实例
        self._actors: Dict[str, Dict[str, AgentActor]] = {}
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls, registry: AgentRegistry = None, actor_class: Type[AgentActor] = None) -> "ActorManager":
        """
        获取全局单例实例。

        - 首次调用必须提供 registry 和 actor_class。
        - 后续调用可不传参。
        """
        # 如果实例已存在，直接返回（无需锁，提升性能）
        if cls._instance is not None:
            return cls._instance

        # 否则走 __new__ + __init__ 流程（内部已有锁）
        return cls(registry, actor_class)

    def bootstrap_all_agents(self, tenant_ids: List[str]):
        """
        【可选】启动时为指定租户预加载所有已注册的智能体。
        适用于希望提前创建所有 Actor 的场景（如低延迟要求）。

        :param tenant_ids: 要预加载的租户 ID 列表
        """
        all_agent_ids = self._get_all_agent_ids_from_registry()
        for tenant_id in tenant_ids:
            for agent_id in all_agent_ids:
                # 懒加载：实际创建仍由 get_or_create_actor 触发
                self.get_or_create_actor(tenant_id, agent_id)

    def _get_all_agent_ids_from_registry(self) -> List[str]:
        """从 registry 获取所有 agent_id 列表（不加载完整数据）"""
        # 可通过简单查询实现
        with self.registry.driver.session() as session:
            result = session.read_transaction(lambda tx: tx.run("MATCH (a:Agent) RETURN a.agent_id AS id"))
            return [record["id"] for record in result]

    def get_or_create_actor(
        self,
        tenant_id: str,
        agent_id: str,
        orchestrator_callback: Optional[Callable[[Dict], None]] = None,
    ) -> AgentActor:
        """
        获取或创建指定租户下的 Actor。
        元数据自动从 Neo4j 加载。

        :raises ValueError: 如果 Neo4j 中不存在该 agent_id
        """
        with self._lock:
            # 初始化租户容器
            if tenant_id not in self._actors:
                self._actors[tenant_id] = {}

            # 已存在则直接返回
            if agent_id in self._actors[tenant_id]:
                return self._actors[tenant_id][agent_id]

            # 从 Neo4j 加载元数据
            agent_meta = self.registry.get_agent_by_id(agent_id)
            if agent_meta is None:
                raise ValueError(f"Agent '{agent_id}' not found in registry (Neo4j)")

            logger.info(f"[{tenant_id}] Creating actor from registry: {agent_id}")

            # 合并租户上下文到 data_scope（确保隔离）
            data_scope = dict(agent_meta["data_scope"])
            data_scope.setdefault("tenant_id", tenant_id)

            # 创建 Actor
            actor = self.actor_class(
                agent_id=agent_id,
                capabilities=agent_meta["capabilities"],
                data_scope=data_scope,
                is_leaf=agent_meta["is_leaf"],
                orchestrator_callback=orchestrator_callback,
            )
            actor.start()
            self._actors[tenant_id][agent_id] = actor
            return actor

    def send_message(self, tenant_id: str, agent_id: str, message: Dict[str, Any]):
        """向指定租户的指定 Actor 发送消息"""
        with self._lock:
            if tenant_id not in self._actors:
                raise KeyError(f"Tenant '{tenant_id}' not found")
            if agent_id not in self._actors[tenant_id]:
                raise KeyError(f"Actor '{agent_id}' not found for tenant '{tenant_id}'")
            actor = self._actors[tenant_id][agent_id]
            actor.send_message(message)

    def has_actor(self, tenant_id: str, agent_id: str) -> bool:
        """检查指定 Actor 是否已存在"""
        with self._lock:
            return (
                tenant_id in self._actors
                and agent_id in self._actors[tenant_id]
            )

    def stop_tenant_actors(self, tenant_id: str):
        """停止并移除指定租户的所有 Actor"""
        with self._lock:
            if tenant_id not in self._actors:
                return
            actors = self._actors.pop(tenant_id)
            for aid, actor in actors.items():
                logger.info(f"[{tenant_id}] Stopping actor: {aid}")
                actor.stop()

    def stop_all(self):
        """停止所有租户的所有 Actor（用于服务优雅关闭）"""
        with self._lock:
            tenant_ids = list(self._actors.keys())
            for tid in tenant_ids:
                self.stop_tenant_actors(tid)

    def get_tenant_actor_ids(self, tenant_id: str) -> List[str]:
        """获取某租户下所有已创建的 actor_id 列表"""
        with self._lock:
            return list(self._actors.get(tenant_id, {}).keys())

    def get_total_actor_count(self) -> int:
        """获取当前总 Actor 数量（用于监控）"""
        with self._lock:
            return sum(len(actors) for actors in self._actors.values())
        

