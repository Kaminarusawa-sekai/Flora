"""基于Neo4j的Agent树形结构管理实现"""
from typing import Dict, List, Any, Optional
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
            包含父子关系信息的字典，格式为 {'parent': parent_id, 'children': [child_ids]}
        """
        with self.driver.session() as session:
            result = session.read_transaction(self._get_relationship_tx, agent_id)
            return result
    
    def _get_relationship_tx(self, tx, agent_id: str) -> Dict[str, Any]:
        """事务函数：查询Agent关系"""
        # 查询父节点
        parent_query = """
        MATCH (parent)-[:HAS_CHILD]->(child {id: $agent_id})
        RETURN parent.id as parent_id
        LIMIT 1
        """
        parent_result = tx.run(parent_query, agent_id=agent_id).single()
        parent_id = parent_result['parent_id'] if parent_result else None
        
        # 查询子节点
        children_query = """
        MATCH (parent {id: $agent_id})-[:HAS_CHILD]->(child)
        RETURN child.id as child_id
        """
        children_result = tx.run(children_query, agent_id=agent_id).data()
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
        with self.driver.session() as session:
            result = session.read_transaction(self._load_all_agents_tx)
            return result
    
    def _load_all_agents_tx(self, tx) -> List[Dict[str, Any]]:
        """事务函数：加载所有Agent"""
        query = """
        MATCH (a:Agent)
        RETURN a.id as agent_id, a.meta as meta
        """
        result = tx.run(query).data()
        # 转换格式，将meta中的字段展开到顶层
        agents = []
        for record in result:
            agent = {'agent_id': record['agent_id']}
            if record['meta']:
                agent.update(record['meta'])
            agents.append(agent)
        return agents
    
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
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定Agent的信息
        
        Args:
            agent_id: Agent唯一标识符
            
        Returns:
            Agent信息字典，如果不存在则返回None
        """
        with self.driver.session() as session:
            result = session.read_transaction(self._get_agent_by_id_tx, agent_id)
            return result if result else None
    
    def _get_agent_by_id_tx(self, tx, agent_id: str) -> Optional[Dict[str, Any]]:
        """事务函数：查询单个Agent"""
        query = """
        MATCH (a:Agent {id: $agent_id})
        RETURN a.id as agent_id, a.meta as meta
        """
        result = tx.run(query, agent_id=agent_id).single()
        if not result:
            return None
        
        # 转换格式，将meta中的字段展开到顶层
        agent = {'agent_id': result['agent_id']}
        if result['meta']:
            agent.update(result['meta'])
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
            with self.driver.session() as session:
                session.write_transaction(self._remove_agent_tx, agent_id)
            return True
        except Exception as e:
            logging.error(f"删除Agent失败: {e}")
            return False
    
    def _remove_agent_tx(self, tx, agent_id: str):
        """事务函数：删除Agent"""
        # 先删除所有与该Agent相关的关系
        query_remove_relationships = """
        MATCH (a:Agent {id: $agent_id})-[r]-()
        DELETE r
        """
        tx.run(query_remove_relationships, agent_id=agent_id)
        
        # 再删除Agent节点
        query_remove_node = """
        MATCH (a:Agent {id: $agent_id})
        DELETE a
        """
        tx.run(query_remove_node, agent_id=agent_id)
    
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
                logging.error("节点数据必须包含agent_id")
                return None
            
            # 提取meta数据（除了agent_id之外的所有字段）
            meta_data = {k: v for k, v in node_data.items() if k != 'agent_id'}
            
            with self.driver.session() as session:
                session.write_transaction(
                    self._create_node_tx, 
                    agent_id, 
                    meta_data
                )
            return agent_id
        except Exception as e:
            logging.error(f"创建节点失败: {e}")
            return None
    
    def _create_node_tx(self, tx, agent_id: str, meta_data: Dict[str, Any]):
        """事务函数：创建节点"""
        query = """
        CREATE (a:Agent {id: $agent_id, meta: $meta_data})
        RETURN a
        """
        tx.run(query, agent_id=agent_id, meta_data=meta_data)
    
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
                logging.error(f"节点 {node_id} 不存在")
                return False
            
            # 提取当前的meta数据
            current_meta = {k: v for k, v in existing_node.items() if k != 'agent_id'}
            # 更新meta数据
            current_meta.update(updates)
            
            with self.driver.session() as session:
                session.write_transaction(
                    self._update_node_tx, 
                    node_id, 
                    current_meta
                )
            return True
        except Exception as e:
            logging.error(f"更新节点失败: {e}")
            return False
    
    def _update_node_tx(self, tx, node_id: str, meta_data: Dict[str, Any]):
        """事务函数：更新节点"""
        query = """
        MATCH (a:Agent {id: $node_id})
        SET a.meta = $meta_data
        RETURN a
        """
        tx.run(query, node_id=node_id, meta_data=meta_data)
    
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
        import networkx as nx
        import logging

        # Step 1: 查询所有满足条件的路径，并提取节点和边
        query = """
        MATCH (start:Agent {code: $rootCode})
        CALL apoc.path.expandConfig(start, {
            relationshipFilter: 'HAS_CHILD>',
            minLevel: 0,          // 包含起点（level=0）
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
            all_agents = self.load_all_agents()
            agent_map = {agent.get('agent_id'): agent for agent in all_agents}

            node_set = set()
            node_properties = {}
            edges = []

            with self.driver.session() as session:
                # 获取节点
                node_records = session.run(query, rootCode=root_code, threshold=threshold, maxHops=max_hops)
                for rec in node_records:
                    nid = rec["node_id"]
                    if nid is None:
                        continue
                    node_set.add(nid)
                    props = dict(rec["node_props"])
                    if "id" in props:
                        del props["id"]  # 避免重复
                    if nid in agent_map:
                        full_props = agent_map[nid].copy()
                        full_props.update(props)  # Neo4j 属性优先
                        node_properties[nid] = full_props
                    else:
                        node_properties[nid] = props

                # 获取边（仅节点集内部的边），并取最大强度
                edge_records = session.run(edge_query, rootCode=root_code, threshold=threshold, maxHops=max_hops)
                for rec in edge_records:
                    f, t, w = rec["from_id"], rec["to_id"], rec["maxTotalStrength"]
                    if f in node_set and t in node_set:
                        edges.append((f, t, float(w)))

            if not node_set:
                logging.warning(f"No influenced nodes found for root {root_code}")
                return {"nodes": [], "edges": []}

            # Step 2: 构建子图并计算 SCC
            subgraph = nx.DiGraph()
            for nid in node_set:
                subgraph.add_node(nid)
            for f, t, w in edges:
                subgraph.add_edge(f, t, weight=w)

            # 计算强连通分量
            scc_id_map = {}
            for idx, component in enumerate(nx.strongly_connected_components(subgraph)):
                scc_label = f"SCC_{idx}"
                for node in component:
                    scc_id_map[node] = scc_label

            # Step 3: 组装返回结果
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


class MemoryAgentStructure(AgentStructureInterface):
    """
    基于内存的Agent树形结构管理实现
    用于快速开发和测试环境
    """
    
    def __init__(self):
        """初始化内存存储"""
        # 存储所有节点数据
        self.nodes = {}
        # 存储关系数据 {node_id: {'parent': parent_id, 'children': [child_ids]}}
        self.relationships = {}
        logging.info("内存存储结构初始化完成")
    
    def get_agent_relationship(self, agent_id: str) -> Dict[str, Any]:
        """
        获取Agent的父子关系
        
        Args:
            agent_id: Agent唯一标识符
            
        Returns:
            包含父子关系信息的字典，格式为 {'parent': parent_id, 'children': [child_ids]}
        """
        if agent_id not in self.relationships:
            return {'parent': None, 'children': []}
        return self.relationships[agent_id]
    
    def load_all_agents(self) -> List[Dict[str, Any]]:
        """
        加载所有Agent信息
        
        Returns:
            所有Agent的列表
        """
        return list(self.nodes.values())
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定Agent的信息
        
        Args:
            agent_id: Agent唯一标识符
            
        Returns:
            Agent信息字典，如果不存在则返回None
        """
        return self.nodes.get(agent_id)
    
    def add_agent_relationship(self, parent_id: str, child_id: str) -> bool:
        """
        添加Agent之间的父子关系
        
        Args:
            parent_id: 父Agent ID
            child_id: 子Agent ID
            
        Returns:
            是否添加成功
        """
        # 验证节点是否存在
        if parent_id not in self.nodes or child_id not in self.nodes:
            logging.error(f"父节点 {parent_id} 或子节点 {child_id} 不存在")
            return False
        
        # 确保关系字典中存在条目
        if parent_id not in self.relationships:
            self.relationships[parent_id] = {'parent': None, 'children': []}
        if child_id not in self.relationships:
            self.relationships[child_id] = {'parent': None, 'children': []}
        
        # 更新关系
        self.relationships[parent_id]['children'].append(child_id)
        self.relationships[child_id]['parent'] = parent_id
        
        logging.info(f"添加关系成功: {parent_id} -> {child_id}")
        return True
    
    def remove_agent(self, agent_id: str) -> bool:
        """
        删除指定Agent及其所有关系
        
        Args:
            agent_id: 要删除的Agent ID
            
        Returns:
            是否删除成功
        """
        if agent_id not in self.nodes:
            logging.error(f"节点 {agent_id} 不存在")
            return False
        
        # 断开与父节点的关系
        if agent_id in self.relationships and self.relationships[agent_id]['parent']:
            parent_id = self.relationships[agent_id]['parent']
            if parent_id in self.relationships:
                self.relationships[parent_id]['children'].remove(agent_id)
        
        # 断开与子节点的关系
        if agent_id in self.relationships:
            for child_id in self.relationships[agent_id]['children']:
                if child_id in self.relationships:
                    self.relationships[child_id]['parent'] = None
        
        # 删除节点和关系
        del self.nodes[agent_id]
        if agent_id in self.relationships:
            del self.relationships[agent_id]
        
        logging.info(f"删除节点成功: {agent_id}")
        return True
    
    def create_node(self, node_data: Dict[str, Any]) -> Optional[str]:
        """
        创建新的Agent节点
        
        Args:
            node_data: 节点数据，必须包含agent_id
            
        Returns:
            创建的节点ID，如果创建失败则返回None
        """
        agent_id = node_data.get('agent_id')
        if not agent_id:
            logging.error("节点数据必须包含agent_id")
            return None
        
        # 检查节点是否已存在
        if agent_id in self.nodes:
            logging.error(f"节点 {agent_id} 已存在")
            return None
        
        # 创建节点
        self.nodes[agent_id] = node_data.copy()
        # 初始化关系
        self.relationships[agent_id] = {'parent': None, 'children': []}
        
        logging.info(f"创建节点成功: {agent_id}")
        return agent_id
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新节点信息
        
        Args:
            node_id: 节点ID
            updates: 更新内容
            
        Returns:
            是否更新成功
        """
        if node_id not in self.nodes:
            logging.error(f"节点 {node_id} 不存在")
            return False
        
        # 更新节点信息，保留agent_id
        agent_id = self.nodes[node_id]['agent_id']
        self.nodes[node_id].update(updates)
        # 确保agent_id不会被覆盖
        self.nodes[node_id]['agent_id'] = agent_id
        
        logging.info(f"更新节点成功: {node_id}")
        return True
    
    def close(self) -> None:
        """
        关闭连接，释放资源
        对于内存存储，这里不需要做特殊处理
        """
        logging.info("内存存储结构已关闭")
    
    def get_influenced_subgraph(
        self,
        root_code: str,
        threshold: float = 0.3,
        max_hops: int = 5
    ) -> 'nx.DiGraph':
        """
        获取以指定节点为根的影响子图
        
        Args:
            root_code: 根节点代码
            threshold: 影响强度阈值
            max_hops: 最大跳数
            
        Returns:
            nx.DiGraph: 影响子图
        """
        import networkx as nx
        
        graph = nx.DiGraph()
        
        try:
            # 查找根节点
            root_node = None
            root_id = None
            
            # 先尝试通过code查找
            for agent_id, agent_data in self.nodes.items():
                if agent_data.get('code') == root_code:
                    root_node = agent_data
                    root_id = agent_id
                    break
            
            # 如果没找到，尝试将root_code作为agent_id查找
            if not root_node and root_code in self.nodes:
                root_node = self.nodes[root_code]
                root_id = root_code
            
            if not root_node:
                raise ValueError(f"根节点 {root_code} 未找到")
            
            # 添加根节点到图中
            graph.add_node(root_id, **root_node)
            
            # 记录已访问的节点，避免循环引用
            visited = set()
            
            # 递归构建影响子图
            def _build_influenced_subgraph_recursive(
                current_id: str,
                current_hops: int,
                current_strength: float,
                visited_nodes: set
            ):
                """递归构建影响子图"""
                # 如果达到最大跳数或强度低于阈值，停止递归
                if current_hops >= max_hops or current_strength < threshold:
                    return
                
                # 标记当前节点为已访问
                visited_nodes.add(current_id)
                
                # 获取当前节点的关系信息
                relationships = self.relationships.get(current_id, {})
                children = relationships.get('children', [])
                
                for child_id in children:
                    # 避免循环引用
                    if child_id in visited_nodes:
                        continue
                    
                    # 获取子节点信息
                    child_node = self.nodes.get(child_id)
                    if not child_node:
                        continue
                    
                    # 计算影响强度（这里简化处理，从子节点获取权重或使用默认值）
                    weight = child_node.get('weight', 0.5)
                    influence_strength = current_strength * weight
                    
                    if influence_strength >= threshold:
                        # 添加子节点到图中
                        if child_id not in graph:
                            graph.add_node(child_id, **child_node)
                        
                        # 添加边，权重为影响强度
                        graph.add_edge(current_id, child_id, weight=influence_strength)
                        
                        # 递归处理子节点
                        _build_influenced_subgraph_recursive(
                            child_id, current_hops + 1, influence_strength, visited_nodes.copy()
                        )
            
            # 开始递归构建
            _build_influenced_subgraph_recursive(root_id, 0, 1.0, set())
            
        except Exception as e:
            logging.error(f"构建内存影响子图失败: {e}")
            # 如果构建失败，返回只包含根节点的图
            pass
        
        return graph
