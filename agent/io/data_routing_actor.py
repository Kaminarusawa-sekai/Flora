# data_routing_actor.py
from thespian.actors import Actor, ActorAddress
from agent.agent_registry import AgentRegistry
from agent.message import RouteDataQuery, DataSourceFound, DataSourceNotFound
from typing import Optional

class DataRoutingActor(Actor):
    def receiveMessage(self, msg, sender):
        if isinstance(msg, RouteDataQuery):
            try:
                registry = AgentRegistry.get_instance()
                candidate_id = self._find_data_agent(registry, msg.start_agent_id)
                if candidate_id:
                    # 明确获取 "data" 角色的 Actor 地址
                    actor_addr = registry.get_actor_ref(candidate_id, "data")
                    if actor_addr:
                        self.send(msg.requester, DataSourceFound(actor_addr))
                    else:
                        self.send(
                            msg.requester,
                            DataSourceNotFound(f"No 'data' actor ref for {candidate_id}")
                        )
                else:
                    self.send(
                        msg.requester,
                        DataSourceNotFound("No valid data agent found in tree")
                    )
            except Exception as e:
                self.send(
                    msg.requester,
                    DataSourceNotFound(f"Routing error: {e}")
                )

    def _is_valid_data_node(self, registry: AgentRegistry, agent_id: str) -> bool:
        """判断是否为有效的数据节点：is_leaf + 已注册 data actor"""
        if not registry.has_agent(agent_id):
            return False
        meta = registry.get_agent_meta(agent_id)
        # 关键：检查 role="data" 的 actor 是否存在
        return bool(
            meta 
            and meta.get("is_leaf") 
            and registry.has_actor_ref(agent_id, "data")
        )

    def _search_down(self, registry: AgentRegistry, agent_id: str) -> Optional[str]:
        """DFS 搜索子树，找第一个有效的 data 节点"""
        if self._is_valid_data_node(registry, agent_id):
            return agent_id
        for child_id in registry.get_children(agent_id):
            result = self._search_down(registry, child_id)
            if result:
                return result
        return None

    def _find_data_agent(self, registry: AgentRegistry, start_id: str) -> Optional[str]:
        # Step 1: Check self
        if self._is_valid_data_node(registry, start_id):
            return start_id

        # Step 2: Search down from self
        candidate = self._search_down(registry, start_id)
        if candidate:
            return candidate

        # Step 3: Walk up the parent chain
        current = start_id
        while True:
            parent_id = registry.get_parent(current)
            if not parent_id:
                break
            candidate = self._search_down(registry, parent_id)
            if candidate:
                return candidate
            current = parent_id

        return None