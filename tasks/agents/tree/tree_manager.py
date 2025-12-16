"""树形结构管理器"""
from typing import Dict, Any, Optional, List
import logging
from .node_service import NodeService
from .relationship_service import RelationshipService
from ...external.repositories.agent_structure_repo import AgentStructureRepository



class TreeManager:
    """
    树形结构管理器
    封装AgentRegistry功能
    负责管理Agent的树形结构和关系
    """
    
    def __init__(self):
        """
        初始化树形结构管理器
        
        Args:
            structure: Agent结构管理器实例，如果为None则自动创建
        """
        self.logger = logging.getLogger(__name__)
        

        self.agent_structure_repo = AgentStructureRepository()
        # 初始化节点服务和关系服务
        self.node_service = NodeService(self.agent_structure_repo)
        self.relationship_service = RelationshipService(self.agent_structure_repo)
        
        # Actor引用管理
        self.actor_refs = {}
        
        self.logger.info("树形结构管理器初始化成功")
    
    def get_agent_meta(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent元数据
        从AgentRegistry.get_agent_meta迁移
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict[str, Any]: Agent元数据
        """
        return self.node_service.get_agent_meta(agent_id)
    
    def get_children(self, agent_id: str) -> List[str]:
        """
        获取Agent的子节点
        从AgentRegistry.get_children迁移
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List[str]: 子节点ID列表
        """
        return self.relationship_service.get_children(agent_id)
    
    def get_parent(self, agent_id: str) -> Optional[str]:
        """
        获取Agent的父节点
        
        Args:
            agent_id: Agent ID
            
        Returns:
            str: 父节点ID
        """
        return self.relationship_service.get_parent(agent_id)
    
    def get_actor_ref(self, agent_id: str) -> Optional[Any]:
        """
        获取Agent的Actor引用
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Any: Actor引用
        """
        return self.actor_refs.get(agent_id)
    
    def set_actor_ref(self, agent_id: str, actor_ref: Any) -> None:
        """
        设置Agent的Actor引用
        
        Args:
            agent_id: Agent ID
            actor_ref: Actor引用
        """
        self.actor_refs[agent_id] = actor_ref
    
    def remove_actor_ref(self, agent_id: str) -> None:
        """
        移除Agent的Actor引用
        
        Args:
            agent_id: Agent ID
        """
        if agent_id in self.actor_refs:
            del self.actor_refs[agent_id]
    
    def get_root_agents(self) -> List[str]:
        """
        获取所有根节点Agent
        
        Returns:
            List[str]: 根节点Agent ID列表
        """
        root_agents = []
        all_agents = self.node_service.get_all_nodes()
        
        for agent in all_agents:
            agent_id = agent.get("agent_id")
            if agent_id and not self.get_parent(agent_id):
                root_agents.append(agent_id)
        
        return root_agents
    
    def is_leaf_agent(self, agent_id: str) -> bool:
        """
        检查Agent是否是叶子节点
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否是叶子节点
        """
        meta = self.get_agent_meta(agent_id)
        if meta:
            return meta.get("is_leaf", False)
        
        # 如果没有元数据，检查是否有子节点
        children = self.get_children(agent_id)
        return len(children) == 0
    
    def get_full_path(self, agent_id: str) -> List[str]:
        """
        获取Agent的完整路径（从根节点到当前节点）
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List[str]: 路径节点ID列表
        """
        path = [agent_id]
        current = agent_id
        
        while True:
            parent = self.get_parent(current)
            if not parent:
                break
            path.insert(0, parent)
            current = parent
        
        return path
    
    def find_agent_by_path(self, path: List[str]) -> Optional[str]:
        """
        根据路径查找Agent
        
        Args:
            path: 路径节点ID列表
            
        Returns:
            str: 找到的Agent ID，如果不存在则返回None
        """
        if not path:
            return None
        
        # 检查第一个节点是否是根节点
        if self.get_parent(path[0]):
            self.logger.warning(f"路径起点 {path[0]} 不是根节点")
            return None
        
        current = path[0]
        
        # 遍历路径进行匹配
        for i in range(1, len(path)):
            expected = path[i]
            children = self.get_children(current)
            
            if expected not in children:
                self.logger.warning(f"路径不存在: {path}")
                return None
            
            current = expected
        
        return current
    
    def get_subtree(self, root_id: str) -> Dict[str, Any]:
        """
        获取以指定节点为根的子树
        
        Args:
            root_id: 根节点ID
            
        Returns:
            Dict[str, Any]: 子树结构
        """
        subtree = {
            "agent_id": root_id,
            "meta": self.get_agent_meta(root_id),
            "children": []
        }
        
        children = self.get_children(root_id)
        for child_id in children:
            subtree["children"].append(self.get_subtree(child_id))
        
        return subtree
    
    def search_agents(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        搜索Agent
        
        Args:
            query: 搜索查询
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 匹配的Agent列表
        """
        results = self.node_service.search_nodes(query, filters)
        
        # 为每个结果添加关系信息
        for result in results:
            agent_id = result.get("agent_id")
            if agent_id:
                result["parent"] = self.get_parent(agent_id)
                result["children"] = self.get_children(agent_id)
        
        return results
    
    def add_agent(self, agent_data: Dict[str, Any], parent_id: Optional[str] = None) -> Optional[str]:
        """
        添加新Agent
        
        Args:
            agent_data: Agent数据
            parent_id: 父Agent ID
            
        Returns:
            str: 新Agent ID，如果添加失败则返回None
        """
        # 创建节点
        agent_id = self.node_service.create_node(agent_data)
        if not agent_id:
            return None
        
        # 添加父子关系
        if parent_id:
            success = self.relationship_service.add_relationship(parent_id, agent_id)
            if not success:
                # 如果关系添加失败，删除节点
                self.node_service.delete_node(agent_id)
                return None
        
        self.logger.info(f"Agent {agent_id} 添加成功")
        return agent_id
    
    def update_agent(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新Agent信息
        
        Args:
            agent_id: Agent ID
            updates: 更新内容
            
        Returns:
            bool: 是否更新成功
        """
        return self.node_service.update_node(agent_id, updates)
    
    def delete_agent(self, agent_id: str) -> bool:
        """
        删除Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否删除成功
        """
        # 先获取所有子节点
        children = self.get_children(agent_id)
        
        # 递归删除所有子节点
        for child_id in children:
            if not self.delete_agent(child_id):
                self.logger.error(f"删除子Agent {child_id} 失败")
                return False
        
        # 获取父节点，用于后续移除关系
        parent_id = self.get_parent(agent_id)
        
        # 删除节点
        if not self.node_service.delete_node(agent_id):
            return False
        
        # 移除与父节点的关系
        if parent_id:
            self.relationship_service.remove_relationship(parent_id, agent_id)
        
        # 移除Actor引用
        self.remove_actor_ref(agent_id)
        
        self.logger.info(f"Agent {agent_id} 删除成功")
        return True
    
    def get_agent_depth(self, agent_id: str) -> int:
        """
        获取Agent的深度（根节点深度为0）
        
        Args:
            agent_id: Agent ID
            
        Returns:
            int: 深度
        """
        depth = 0
        current = agent_id
        
        while True:
            parent = self.get_parent(current)
            if not parent:
                break
            depth += 1
            current = parent
        
        return depth
    
    def get_level_agents(self, level: int) -> List[str]:
        """
        获取指定层级的所有Agent
        
        Args:
            level: 层级（从0开始）
            
        Returns:
            List[str]: Agent ID列表
        """
        level_agents = []
        all_agents = self.node_service.get_all_nodes()
        
        for agent in all_agents:
            agent_id = agent.get("agent_id")
            if agent_id and self.get_agent_depth(agent_id) == level:
                level_agents.append(agent_id)
        
        return level_agents
    
    def refresh(self):
        """
        刷新所有缓存
        """
        self.node_service.refresh_cache()
        self.relationship_service.refresh_cache()
        self.logger.info("树形结构缓存已刷新")
    
    def close(self):
        """
        关闭树形结构管理器
        """
        self.node_service.close()
        self.relationship_service.close()
        self.actor_refs.clear()
        self.logger.info("树形结构管理器已关闭")
    
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
        
        # 尝试通过structure获取影响子图
        try:
            # 检查structure是否支持直接获取影响子图
            if hasattr(self.node_service.structure, 'get_influenced_subgraph'):
                return self.node_service.structure.get_influenced_subgraph(
                    root_code, threshold, max_hops
                )
        except Exception as e:
            self.logger.error(f"直接获取影响子图失败: {e}")
        
        # 如果structure不支持，尝试手动构建
        try:
            # 先加入根节点
            # 这里假设node_service有get_node_by_code方法
            root_node = None
            if hasattr(self.node_service, 'get_node_by_code'):
                root_node = self.node_service.get_node_by_code(root_code)
            
            if not root_node:
                # 尝试通过搜索找到根节点
                all_nodes = self.node_service.get_all_nodes()
                for node in all_nodes:
                    if node.get('code') == root_code:
                        root_node = node
                        break
            
            if not root_node:
                raise ValueError(f"根节点 {root_code} 未找到")
            
            # 添加根节点到图中
            node_id = root_node.get('agent_id') or root_node.get('id') or root_code
            graph.add_node(node_id, **root_node)
            
            # 这里可以根据需要实现简单的影响传播逻辑
            # 例如，基于节点之间的关系和权重来构建影响子图
            
            # 遍历子节点，构建简单的影响关系
            self._build_influenced_subgraph_recursive(
                graph, node_id, threshold, max_hops, 0, 1.0
            )
            
        except Exception as e:
            self.logger.error(f"构建影响子图失败: {e}")
            raise
        
        return graph
    
    def _build_influenced_subgraph_recursive(
        self,
        graph: 'nx.DiGraph',
        current_id: str,
        threshold: float,
        max_hops: int,
        current_hops: int,
        current_strength: float
    ):
        """
        递归构建影响子图
        
        Args:
            graph: 图对象
            current_id: 当前节点ID
            threshold: 影响强度阈值
            max_hops: 最大跳数
            current_hops: 当前跳数
            current_strength: 当前影响强度
        """
        if current_hops >= max_hops or current_strength < threshold:
            return
        
        # 获取当前节点的子节点
        children = self.get_children(current_id)
        
        for child_id in children:
            # 获取子节点信息
            child_meta = self.get_agent_meta(child_id)
            if not child_meta:
                continue
            
            # 计算影响强度（这里简化处理，可以根据实际情况调整）
            # 例如，可以从子节点的meta中获取权重信息
            weight = child_meta.get('weight', 0.5)
            influence_strength = current_strength * weight
            
            if influence_strength >= threshold:
                # 添加子节点到图中
                if child_id not in graph:
                    graph.add_node(child_id, **child_meta)
                
                # 添加边，权重为影响强度
                graph.add_edge(current_id, child_id, weight=influence_strength)
                
                # 递归处理子节点
                self._build_influenced_subgraph_recursive(
                    graph, child_id, threshold, max_hops, current_hops + 1, influence_strength
                )

##TODO:全局唯一实例，统一初始化
treeManager = TreeManager()
