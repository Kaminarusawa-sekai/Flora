class DataReferenceResolver:
    def __init__(self, agent_registry: "AgentRegistry"):
        self.registry = agent_registry

    def find_data_provider(self, start_agent_id: str, data_key: str, context: Dict) -> Optional[BaseAgent]:
        # 先向下查子树
        candidate = self._dfs_search(start_agent_id, data_key)
        if candidate:
            return candidate

        # 再向上回溯查兄弟
        current = start_agent_id
        while current:
            parent_id = self.registry.get_parent(current)
            if not parent_id:
                break
            siblings = self.registry.get_children(parent_id)
            for sib in siblings:
                if sib == current:
                    continue
                agent = self.registry.get_agent(sib)
                if data_key in agent.declare_provided_data():
                    return agent
            current = parent_id

        return None

    def _dfs_search(self, agent_id: str, data_key: str) -> Optional[BaseAgent]:
        agent = self.registry.get_agent(agent_id)
        if data_key in agent.declare_provided_data():
            return agent
        for child_id in self.registry.get_children(agent_id):
            res = self._dfs_search(child_id, data_key)
            if res:
                return res
        return None