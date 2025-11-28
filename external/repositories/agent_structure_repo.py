"""Agent结构仓储，负责操作Neo4j，维护父子关系"""
from typing import Dict, List, Any, Optional
import logging
import networkx as nx
from external.database.neo4j_client import Neo4jClient


class AgentStructureRepository:
    """
    Agent结构仓储类，负责操作Neo4j，维护Agent的父子关系
    """
    
    def __init__(self, neo4j_client: Neo4jClient=None):
        """
        初始化Agent结构仓储
        
        Args:
            neo4j_client: Neo4j客户端实例
        """
        if not neo4j_client:
            self.neo4j_client = Neo4jClient()
        else:
            self.neo4j_client = neo4j_client
    
    def get_agent_relationship(self, agent_id: str) -> Dict[str, Any]:
        """
        获取Agent的父子关系
        
        Args:
            agent_id: Agent唯一标识符
            
        Returns:
            包含父子关系信息的字典，格式为 {'parent': parent_id, 'children': [child_ids]}
        """
        # 查询父节点
        parent_query = """
        MATCH (parent)-[:HAS_CHILD]->(child {id: $agent_id})
        RETURN parent.id as parent_id
        LIMIT 1
        """
        parent_result = self.neo4j_client.execute_query(parent_query, {'agent_id': agent_id})
        parent_id = parent_result[0]['parent_id'] if parent_result else None
        
        # 查询子节点
        children_query = """
        MATCH (parent {id: $agent_id})-[:HAS_CHILD]->(child)
        RETURN child.id as child_id
        """
        children_result = self.neo4j_client.execute_query(children_query, {'agent_id': agent_id})
        child_ids = [record['child_id'] for record in children_result]
        
        return {
            'parent': parent_id,
            'children': child_ids
        }
    
    def load_all_agents(self) -> List[Dict[str, Any]]:
        """
        加载所有Agent节点
        
        Returns:
            Agent节点信息列表
        """
        query = """
        MATCH (a:Agent)
        RETURN a.id as agent_id, a.meta as meta
        """
        results = self.neo4j_client.execute_query(query)
        
        # 转换格式，将meta中的字段展开到顶层
        agents = []
        for record in results:
            agent = {'agent_id': record['agent_id']}
            if record['meta']:
                agent.update(record['meta'])
            agents.append(agent)
        return agents
    
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
            query = """
            MATCH (parent {id: $parent_id})
            MATCH (child {id: $child_id})
            MERGE (parent)-[:HAS_CHILD]->(child)
            """
            self.neo4j_client.execute_write(query, {
                'parent_id': parent_id,
                'child_id': child_id
            })
            return True
        except Exception:
            return False
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定Agent的信息
        
        Args:
            agent_id: Agent唯一标识符
            
        Returns:
            Agent信息字典，如果不存在则返回None
        """
        query = """
        MATCH (a:Agent {id: $agent_id})
        RETURN a.id as agent_id, a.meta as meta
        """
        result = self.neo4j_client.execute_query(query, {'agent_id': agent_id})
        if not result:
            return None
        
        record = result[0]
        # 转换格式，将meta中的字段展开到顶层
        agent = {'agent_id': record['agent_id']}
        if record['meta']:
            agent.update(record['meta'])
        return agent
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        删除指定Agent及其所有关系
        
        Args:
            agent_id: 要删除的Agent ID
            
        Returns:
            是否删除成功
        """
        try:
            # 先删除所有与该Agent相关的关系
            query_remove_relationships = """
            MATCH (a:Agent {id: $agent_id})-[r]-()
            DELETE r
            """
            self.neo4j_client.execute_write(query_remove_relationships, {'agent_id': agent_id})
            
            # 再删除Agent节点
            query_remove_node = """
            MATCH (a:Agent {id: $agent_id})
            DELETE a
            """
            self.neo4j_client.execute_write(query_remove_node, {'agent_id': agent_id})
            
            return True
        except Exception:
            return False
    
    def create_node(self, node_data: Dict[str, Any]) -> Optional[str]:
        """
        创建新的Agent节点
        
        Args:
            node_data: 节点数据，必须包含agent_id
            
        Returns:
            创建的节点ID，如果创建失败则返回None
        """
        try:
            agent_id = node_data.get('agent_id')
            if not agent_id:
                return None
            
            # 提取meta数据（除了agent_id之外的所有字段）
            meta_data = {k: v for k, v in node_data.items() if k != 'agent_id'}
            
            query = """
            CREATE (a:Agent {id: $agent_id, meta: $meta_data})
            RETURN a
            """
            self.neo4j_client.execute_write(query, {
                'agent_id': agent_id,
                'meta_data': meta_data
            })
            return agent_id
        except Exception:
            return None
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新节点信息
        
        Args:
            node_id: 节点ID
            updates: 更新内容
            
        Returns:
            是否更新成功
        """
        try:
            # 获取现有节点信息
            existing_node = self.get_agent_by_id(node_id)
            if not existing_node:
                return False
            
            # 提取当前的meta数据
            current_meta = {k: v for k, v in existing_node.items() if k != 'agent_id'}
            # 更新meta数据
            current_meta.update(updates)
            
            query = """
            MATCH (a:Agent {id: $node_id})
            SET a.meta = $meta_data
            RETURN a
            """
            self.neo4j_client.execute_write(query, {
                'node_id': node_id,
                'meta_data': current_meta
            })
            return True
        except Exception:
            return False
        

    def get_influenced_subgraph_with_scc(
        self,
        root_code: str,
        threshold: float = 0.3,
        max_hops: int = 5
    ) -> Dict[str, List[Dict]]:
        """
        获取从 root_code 出发的影响子图，并为每个节点标注 scc_id。
        - 影响传播：路径上边的 strength 相乘
        - 仅保留总影响 >= threshold 的节点
        - 对于多跳情况，使用可达路径中的最大影响强度作为边权重
        - SCC 在该子图内部计算（Python 端）
        """
        # Step 1: 查询所有满足条件的路径，并提取节点和边
        node_query = """
        MATCH (start:Agent {code: $rootCode})
        CALL apoc.path.expandConfig(start, {
            relationshipFilter: 'HAS_CHILD>',
            minLevel: 0,
            maxLevel: $maxHops,
            uniqueness: 'NODE_GLOBAL'
        }) YIELD path
        WITH path,
            reduce(acc = 1.0, r IN relationships(path) | 
                acc * coalesce(r.strength, 0.5)) AS totalStrength
        WHERE totalStrength >= $threshold
        UNWIND nodes(path) AS node
        WITH DISTINCT node.id AS node_id, node AS node_props
        RETURN DISTINCT node_id, node_props
        """

        edge_query = """
        MATCH (start:Agent {code: $rootCode})
        CALL apoc.path.expandConfig(start, {
            relationshipFilter: 'HAS_CHILD>',
            minLevel: 1,
            maxLevel: $maxHops,
            uniqueness: 'RELATIONSHIP_GLOBAL'
        }) YIELD path
        WITH startNode(path) AS from_node, endNode(path) AS to_node,
            reduce(acc = 1.0, r IN relationships(path) | 
                acc * coalesce(r.strength, 0.5)) AS totalStrength
        WITH from_node.id AS from_id, to_node.id AS to_id, max(totalStrength) AS maxTotalStrength
        WHERE maxTotalStrength >= $threshold
        RETURN DISTINCT from_id, to_id, maxTotalStrength
        """

        try:
            # 加载所有 agent 用于属性合并
            all_agents = self.load_all_agents()
            agent_map = {agent.get('agent_id'): agent for agent in all_agents}

            # 执行节点查询
            node_records = self.neo4j_client.execute_query(
                node_query,
                {'rootCode': root_code, 'threshold': threshold, 'maxHops': max_hops}
            )
            node_set = set()
            node_properties = {}
            for rec in node_records:
                nid = rec.get("node_id")
                if nid is None:
                    continue
                node_set.add(nid)
                props = dict(rec["node_props"]) if isinstance(rec["node_props"], dict) else {}
                if "id" in props:
                    del props["id"]
                if nid in agent_map:
                    full_props = agent_map[nid].copy()
                    full_props.update(props)
                    node_properties[nid] = full_props
                else:
                    node_properties[nid] = props

            # 执行边查询
            edge_records = self.neo4j_client.execute_query(
                edge_query,
                {'rootCode': root_code, 'threshold': threshold, 'maxHops': max_hops}
            )
            edges = []
            for rec in edge_records:
                f, t, w = rec["from_id"], rec["to_id"], rec["maxTotalStrength"]
                if f in node_set and t in node_set:
                    edges.append((f, t, float(w)))

            if not node_set:
                logging.warning(f"No influenced nodes found for root {root_code}")
                return {"nodes": [], "edges": []}

            # 构建 NetworkX 图并计算 SCC
            subgraph = nx.DiGraph()
            subgraph.add_nodes_from(node_set)
            subgraph.add_weighted_edges_from(edges)

            scc_id_map = {}
            for idx, component in enumerate(nx.strongly_connected_components(subgraph)):
                scc_label = f"SCC_{idx}"
                for node in component:
                    scc_id_map[node] = scc_label

            # 组装结果
            nodes_result = []
            for nid in node_set:
                props = node_properties.get(nid, {"agent_id": nid})
                props["scc_id"] = scc_id_map.get(nid, f"SCC_SINGLE_{nid}")
                nodes_result.append({
                    "node_id": nid,
                    "properties": props
                })

            edges_result = [
                {"from": f, "to": t, "weight": w}
                for (f, t, w) in edges
            ]

            return {
                "nodes": nodes_result,
                "edges": edges_result
            }

        except Exception as e:
            logging.error(f"Error in get_influenced_subgraph_with_scc: {e}", exc_info=True)
            return {"nodes": [], "edges": []}


def close(self) -> None:
    """
    关闭底层 Neo4j 客户端连接（如果支持）
    """
    
    if hasattr(self.neo4j_client, 'disconnect'):
        self.neo4j_client.disconnect()
        logging.info("Neo4j client connection closed via AgentStructureRepository")
