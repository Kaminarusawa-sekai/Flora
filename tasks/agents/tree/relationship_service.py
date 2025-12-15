"""关系管理服务"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
from ...external.repositories.agent_structure_repo import AgentStructureRepository
from ...common.config.config_manager import config_manager


class RelationshipService:
    """
    关系管理服务
    负责Agent之间关系的查询和管理
    基于现有AgentRegistry功能重构
    """
    
    def __init__(self, structure: Optional[AgentStructureRepository] = None):
        """
        初始化关系服务
        
        Args:
            structure: Agent结构管理器实例，如果为None则自动创建
        """
        self.logger = logging.getLogger(__name__)
        self.structure = structure
        self._initialize_structure()
        self.relationship_cache = {}  # 缓存格式: {node_id: {'data': ..., 'timestamp': ...}}
        self.cache_ttl = timedelta(seconds=60)  # 缓存有效期60秒
        self._start_auto_refresh()
    
    def _initialize_structure(self):
        """
        初始化结构管理器
        """
        if not self.structure:
            try:
                # 从配置中获取Neo4j配置
                from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
                if NEO4J_URI and NEO4J_USER and NEO4J_PASSWORD:
                    self.structure = AgentStructureRepository(
                        uri=NEO4J_URI,
                        user=NEO4J_USER,
                        password=NEO4J_PASSWORD
                    )
                    self.logger.info("Neo4j结构管理器初始化成功")
                else:
                    self.logger.warning("Neo4j配置未找到，使用内存存储")
                    self.structure = self._create_memory_structure()
            except Exception as e:
                self.logger.error(f"初始化结构管理器失败: {e}")
                self.structure = self._create_memory_structure()
    
    def _create_memory_structure(self) :
        """
        创建内存版本的结构管理器
        """
        class MemoryAgentStructure():
            def __init__(self):
                self.relationships = {}
                self.agents = []
            
            def get_agent_relationship(self, agent_id):
                return self.relationships.get(agent_id, {"parent": None, "children": []})
            
            def load_all_agents(self):
                return self.agents
            
            def close(self):
                pass
            
            def add_agent_relationship(self, parent_id: str, child_id: str, relationship_type: str) -> bool:
                # Update parent's children
                if parent_id not in self.relationships:
                    self.relationships[parent_id] = {"parent": None, "children": []}
                if child_id not in self.relationships:
                    self.relationships[child_id] = {"parent": None, "children": []}
                
                self.relationships[parent_id]["children"].append(child_id)
                self.relationships[child_id]["parent"] = parent_id
                return True
            
            def remove_agent(self, agent_id: str) -> bool:
                # Remove from agents list
                if agent_id in self.agents:
                    self.agents.remove(agent_id)
                
                # Remove from relationships
                if agent_id in self.relationships:
                    # Get the agent's relationships
                    agent_rels = self.relationships[agent_id]
                    parent_id = agent_rels.get("parent")
                    
                    # Remove from parent's children
                    if parent_id and parent_id in self.relationships:
                        if agent_id in self.relationships[parent_id]["children"]:
                            self.relationships[parent_id]["children"].remove(agent_id)
                    
                    # Remove the agent's own relationship entry
                    del self.relationships[agent_id]
                
                return True
        
        return MemoryAgentStructure()
    
    def get_children(self, node_id: str) -> List[str]:
        """
        获取节点的子节点
        从AgentRegistry.get_children迁移
        
        Args:
            node_id: 节点ID
            
        Returns:
            List[str]: 子节点ID列表
        """
        # 先从缓存获取
        if node_id in self.relationship_cache:
            cached = self.relationship_cache[node_id]
            if datetime.now() - cached['timestamp'] < self.cache_ttl:
                return cached['data'].get("children", [])
            self.logger.info(f"节点 {node_id} 的关系缓存将过期，自动刷新")
        
        try:
            relationship = self.structure.get_agent_relationship(node_id)
            
            # 缓存关系信息
            self.relationship_cache[node_id] = {
                'data': relationship,
                'timestamp': datetime.now()
            }
            
            return relationship.get("children", [])
        except Exception as e:
            self.logger.error(f"获取子节点失败: {e}")
            return []
    
    def get_parent(self, node_id: str) -> Optional[str]:
        """
        获取节点的父节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            str: 父节点ID，如果没有则返回None
        """
        # 先从缓存获取
        if node_id in self.relationship_cache:
            cached = self.relationship_cache[node_id]
            if datetime.now() - cached['timestamp'] < self.cache_ttl:
                return cached['data'].get("parent")
            self.logger.info(f"节点 {node_id} 的关系缓存将过期，自动刷新")
        
        try:
            relationship = self.structure.get_agent_relationship(node_id)
            
            # 缓存关系信息
            self.relationship_cache[node_id] = {
                'data': relationship,
                'timestamp': datetime.now()
            }
            
            return relationship.get("parent")
        except Exception as e:
            self.logger.error(f"获取父节点失败: {e}")
            return None
    
    def add_relationship(self, parent_id: str, child_id: str) -> bool:
        """
        添加父子关系
        
        Args:
            parent_id: 父节点ID
            child_id: 子节点ID
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 更新缓存
            # 更新父节点的子节点列表
            if parent_id not in self.relationship_cache:
                self.relationship_cache[parent_id] = {'data': {'parent': None, 'children': []}, 'timestamp': datetime.now()}
            if child_id not in self.relationship_cache[parent_id]['data']['children']:
                self.relationship_cache[parent_id]['data']['children'].append(child_id)
            
            # 更新子节点的父节点
            if child_id not in self.relationship_cache:
                self.relationship_cache[child_id] = {'data': {'parent': None, 'children': []}, 'timestamp': datetime.now()}
            self.relationship_cache[child_id]['data']['parent'] = parent_id
            
            # 更新内存存储中的关系
            if hasattr(self.structure, 'relationships'):
                # 确保父节点关系存在
                if parent_id not in self.structure.relationships:
                    self.structure.relationships[parent_id] = {'parent': None, 'children': []}
                if child_id not in self.structure.relationships[parent_id]['children']:
                    self.structure.relationships[parent_id]['children'].append(child_id)
                
                # 确保子节点关系存在
                if child_id not in self.structure.relationships:
                    self.structure.relationships[child_id] = {'parent': None, 'children': []}
                self.structure.relationships[child_id]['parent'] = parent_id
            
            # 尝试使用结构管理器的add_agent_relationship方法
            if hasattr(self.structure, 'add_agent_relationship'):
                return self.structure.add_agent_relationship(parent_id, child_id, 'HAS_CHILD')
            
            self.logger.info(f"添加关系成功: {parent_id} -> {child_id}")
            return True
        except Exception as e:
            self.logger.error(f"添加关系失败: {e}")
            return False
    
    def remove_relationship(self, parent_id: str, child_id: str) -> bool:
        """
        移除父子关系
        
        Args:
            parent_id: 父节点ID
            child_id: 子节点ID
            
        Returns:
            bool: 是否移除成功
        """
        try:
            # 更新缓存
            # 从父节点的子节点列表中移除
            if parent_id in self.relationship_cache:
                if child_id in self.relationship_cache[parent_id]['data']['children']:
                    self.relationship_cache[parent_id]['data']['children'].remove(child_id)
            
            # 清除子节点的父节点
            if child_id in self.relationship_cache:
                self.relationship_cache[child_id]['data']['parent'] = None
            
            # 更新内存存储中的关系
            if hasattr(self.structure, 'relationships'):
                # 从父节点的子节点列表中移除
                if parent_id in self.structure.relationships:
                    if child_id in self.structure.relationships[parent_id]['children']:
                        self.structure.relationships[parent_id]['children'].remove(child_id)
                
                # 清除子节点的父节点
                if child_id in self.structure.relationships:
                    self.structure.relationships[child_id]['parent'] = None
            
            self.logger.info(f"移除关系成功: {parent_id} -> {child_id}")
            return True
        except Exception as e:
            self.logger.error(f"移除关系失败: {e}")
            return False
    
    def get_siblings(self, node_id: str) -> List[str]:
        """
        获取节点的兄弟节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            List[str]: 兄弟节点ID列表
        """
        parent_id = self.get_parent(node_id)
        if not parent_id:
            return []  # 根节点没有兄弟节点
        
        siblings = self.get_children(parent_id)
        # 移除自己
        return [s for s in siblings if s != node_id]
    
    def get_ancestors(self, node_id: str) -> List[str]:
        """
        获取节点的所有祖先节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            List[str]: 祖先节点ID列表（从父节点到根节点）
        """
        ancestors = []
        current = self.get_parent(node_id)
        
        while current:
            ancestors.append(current)
            current = self.get_parent(current)
        
        return ancestors
    
    def get_descendants(self, node_id: str) -> List[str]:
        """
        获取节点的所有后代节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            List[str]: 后代节点ID列表
        """
        descendants = []
        children = self.get_children(node_id)
        
        for child in children:
            descendants.append(child)
            # 递归获取子节点的后代
            descendants.extend(self.get_descendants(child))
        
        return descendants
    
    def is_descendant(self, ancestor_id: str, descendant_id: str) -> bool:
        """
        检查一个节点是否是另一个节点的后代
        
        Args:
            ancestor_id: 祖先节点ID
            descendant_id: 后代节点ID
            
        Returns:
            bool: 是否是后代关系
        """
        if ancestor_id == descendant_id:
            return False  # 自己不是自己的后代
        
        descendants = self.get_descendants(ancestor_id)
        return descendant_id in descendants
    
    def is_ancestor(self, descendant_id: str, ancestor_id: str) -> bool:
        """
        检查一个节点是否是另一个节点的祖先
        
        Args:
            descendant_id: 后代节点ID
            ancestor_id: 祖先节点ID
            
        Returns:
            bool: 是否是祖先关系
        """
        return self.is_descendant(ancestor_id, descendant_id)
    
    def get_path_between(self, start_id: str, end_id: str) -> Optional[List[str]]:
        """
        获取两个节点之间的路径
        
        Args:
            start_id: 起始节点ID
            end_id: 结束节点ID
            
        Returns:
            List[str]: 路径节点ID列表，如果不存在路径则返回None
        """
        # 检查是否有祖先关系
        if self.is_ancestor(start_id, end_id):
            # 从start到end是向上的路径
            path = []
            current = start_id
            while current != end_id:
                path.append(current)
                current = self.get_parent(current)
                if not current:
                    return None
            path.append(end_id)
            return path
        elif self.is_descendant(start_id, end_id):
            # 从start到end是向下的路径
            # 这个比较复杂，需要BFS或DFS
            from collections import deque
            
            queue = deque([(start_id, [start_id])])
            
            while queue:
                current, path = queue.popleft()
                
                if current == end_id:
                    return path
                
                for child in self.get_children(current):
                    if child not in path:
                        queue.append((child, path + [child]))
            
            return None
        else:
            # 找到最近公共祖先
            start_ancestors = set(self.get_ancestors(start_id))
            end_ancestors = set(self.get_ancestors(end_id))
            
            common_ancestors = start_ancestors.intersection(end_ancestors)
            
            if not common_ancestors:
                return None
            
            # 找到最近的公共祖先
            # 这里简化处理，实际上需要更复杂的逻辑
            lca = None
            for ancestor in start_ancestors:
                if ancestor in common_ancestors:
                    if not lca or len(self.get_ancestors(ancestor)) > len(self.get_ancestors(lca)):
                        lca = ancestor
            
            if not lca:
                return None
            
            # 构建路径：start -> lca -> end
            start_to_lca = []
            current = start_id
            while current != lca:
                start_to_lca.append(current)
                current = self.get_parent(current)
            start_to_lca.append(lca)
            
            # 获取lca到end的路径
            end_to_lca = []
            current = end_id
            while current != lca:
                end_to_lca.append(current)
                current = self.get_parent(current)
            end_to_lca.reverse()
            
            return start_to_lca + end_to_lca[1:]  # 避免重复的lca
    
    def _start_auto_refresh(self):
        """
        启动自动刷新缓存的定时任务
        """
        import threading
        import time
        
        def refresh_cache():
            while True:
                time.sleep(60)  # 每隔60秒刷新一次缓存
                self.refresh_cache()
                # self.logger.info("关系缓存已自动刷新")
        
        # 使用守护线程运行，避免影响主程序退出
        thread = threading.Thread(target=refresh_cache, daemon=True)
        thread.start()
    
    def refresh_cache(self):
        """
        刷新关系缓存
        """
        self.relationship_cache.clear()
        # self.logger.info("关系缓存已刷新")
    
    def close(self):
        """
        关闭服务
        """
        if self.structure:
            self.structure.close()
        self.relationship_cache.clear()
        self.logger.info("关系服务已关闭")