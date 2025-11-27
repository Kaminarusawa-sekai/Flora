# coordination/swarm_coordinator.py

class SwarmCoordinator:
    def __init__(self, registry, data_resolver):
        self.registry = registry
        self.data_resolver = data_resolver

    def select_leaf_agents(self, capability: str, count: int):
        leaves = self.registry.get_all_leaves_by_capability(capability)
        if not leaves:
            raise RuntimeError(f"No leaf agents for {capability}")
        # 简单轮询
        return [leaves[i % len(leaves)] for i in range(count)]