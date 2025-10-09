import networkx as nx

# =================== 规则图谱 ===================
class RuleGraph:
    def __init__(self):
        self.graph = nx.DiGraph()

    def add_rule(self, rule_id: str, description: str):
        self.graph.add_node(rule_id, description=description, frequency=0)

    def link_rules(self, source: str, target: str, relation: str = "similar"):
        if not self.graph.has_edge(source, target) or self.graph[source][target].get('relation') != relation:
            self.graph.add_edge(source, target, relation=relation)

    def get_related_rules(self, rule_id: str, relation: str = None):
        related = []
        for src, tgt, data in self.graph.edges(data=True):
            if src == rule_id or tgt == rule_id:
                if relation is None or data.get("relation") == relation:
                    related.append((src, tgt, data))
        return related

    def update_frequency(self, rule_id: str):
        if rule_id in self.graph.nodes:
            self.graph.nodes[rule_id]['frequency'] += 1

    def visualize(self):
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10, 6))
        pos = nx.spring_layout(self.graph)
        nx.draw(self.graph, pos, with_labels=True, node_size=2000, node_color='lightblue')
        edge_labels = nx.get_edge_attributes(self.graph, 'relation')
        nx.draw_networkx_edge_labels(self.graph, pos, edge_labels=edge_labels)
        plt.show()