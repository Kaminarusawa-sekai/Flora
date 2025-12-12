"""节点管理服务"""
from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta

from tasks.external.repositories.agent_structure_repo import AgentStructureRepository
from tasks.common.config.config_manager import config_manager


class NodeService:
    """
    节点管理服务
    负责Agent节点的加载、查询和管理
    基于现有AgentRegistry功能重构
    """
    
    def __init__(self, structure: Optional[AgentStructureRepository] = None):
        """
        初始化节点服务
        
        Args:
            structure: Agent结构管理器实例，如果为None则自动创建
        """
        self.logger = logging.getLogger(__name__)
        self.structure = structure
        self._initialize_structure()
        self.node_cache = {}  # 缓存格式: {node_id: {'data': ..., 'timestamp': ...}}
        self.all_nodes_cache = None  # 总节点缓存
        self.cache_ttl = timedelta(seconds=60)  # 缓存有效期60秒
        self.refresh_threshold = timedelta(seconds=55)  # 55秒后开始尝试刷新
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
                    # 这里可以实现一个内存版本的结构管理器
                    self.structure = self._create_memory_structure()
            except Exception as e:
                self.logger.error(f"初始化结构管理器失败: {e}")
                self.structure = self._create_memory_structure()
    
    def _create_memory_structure(self) :
        """
        创建内存版本的结构管理器
        用于开发和测试环境
        """
        class MemoryAgentStructure():
            def __init__(self):
                self.agents = {}
                self.relationships = {}
            
            def get_agent_relationship(self, agent_id):
                return self.relationships.get(agent_id, {})
            
            def load_all_agents(self):
                return list(self.agents.values())
            
            def close(self):
                pass
            
            def add_agent_relationship(self, parent_id: str, child_id: str, relationship_type: str) -> bool:
                if parent_id not in self.relationships:
                    self.relationships[parent_id] = {'children': []}
                self.relationships[parent_id]['children'].append(child_id)
                return True
            
            def remove_agent(self, agent_id: str) -> bool:
                if agent_id in self.agents:
                    del self.agents[agent_id]
                # Remove from relationships
                for parent_id, rels in list(self.relationships.items()):
                    if agent_id in rels.get('children', []):
                        rels['children'].remove(agent_id)
                    if parent_id == agent_id:
                        del self.relationships[parent_id]
                return True
        
        return MemoryAgentStructure()
    
    def load_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """
        加载节点信息
        
        Args:
            node_id: 节点ID
            
        Returns:
            Dict[str, Any]: 节点信息，如果不存在则返回None
        """
        # 先从缓存获取
        if node_id in self.node_cache:
            cached = self.node_cache[node_id]
            if datetime.now() - cached['timestamp'] < self.cache_ttl:
                return cached['data']
            # 如果接近过期，异步刷新（此处简化处理，同步刷新）
            self.logger.info(f"节点 {node_id} 缓存将过期，自动刷新")
        
        try:
            # 从结构管理器获取所有节点
            all_agents = self.structure.load_all_agents()
            
            # 查找特定节点
            for agent in all_agents:
                if agent.get("agent_id") == node_id:
                    # 缓存节点信息
                    self.node_cache[node_id] = {
                        'data': agent,
                        'timestamp': datetime.now()
                    }
                    return agent
            
            self.logger.warning(f"节点 {node_id} 不存在")
            return None
        except Exception as e:
            self.logger.error(f"加载节点失败: {e}")
            return None
    
    def get_agent_meta(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent元数据
        从AgentRegistry.get_agent_meta迁移
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict[str, Any]: Agent元数据
        """
        node = self.load_node(agent_id)
        if node:
            # 提取元数据信息
            meta = {
                "agent_id": node.get("agent_id"),
                "name": node.get("name", ""),
                "description": node.get("description", ""),
                "datascope": node.get("datascope", {}),
                "capability": node.get("capability", []),
                "is_leaf": node.get("is_leaf", False),
                "code": node.get("code", ""),
                "config": node.get("config", {}),
                "dify": node.get("dify", {}),
                "seq": node.get("seq", 100)
            }
            return meta
        return None
    
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新节点信息
        
        Args:
            node_id: 节点ID
            updates: 更新内容
            
        Returns:
            bool: 是否更新成功
        """
        try:
            # 更新缓存
            if node_id in self.node_cache:
                self.node_cache[node_id].update(updates)
            
            # 更新内存存储中的节点信息
            if hasattr(self.structure, 'agents'):
                for agent in self.structure.agents:
                    if agent.get('agent_id') == node_id:
                        agent.update(updates)
                        break
            
            self.logger.info(f"节点 {node_id} 更新成功")
            return True
        except Exception as e:
            self.logger.error(f"更新节点失败: {e}")
            return False
    
    def create_node(self, node_data: Dict[str, Any]) -> Optional[str]:
        """
        创建新节点
        
        Args:
            node_data: 节点数据
            
        Returns:
            str: 新节点ID，如果创建失败则返回None
        """
        try:
            node_id = node_data.get("agent_id")
            if not node_id:
                self.logger.error("节点数据必须包含agent_id")
                return None
            
            # 在数据库中创建节点
            # 注意：这里需要确保structure实现了创建节点的方法
            # 如果结构管理器支持直接创建节点，我们可以调用它
            # 否则我们先更新缓存，在关闭时同步到数据库
            
            # 更新缓存
            self.node_cache[node_id] = node_data
            
            # 如果是内存存储，直接添加到结构管理器中
            if hasattr(self.structure, 'agents'):
                self.structure.agents.append(node_data)
            
            self.logger.info(f"节点 {node_id} 创建成功")
            return node_id
        except Exception as e:
            self.logger.error(f"创建节点失败: {e}")
            return None
    
    def delete_node(self, node_id: str) -> bool:
        """
        删除节点
        
        Args:
            node_id: 节点ID
            
        Returns:
            bool: 是否删除成功
        """
        try:
            # 删除缓存
            if node_id in self.node_cache:
                del self.node_cache[node_id]
            
            # 从内存存储中删除节点
            if hasattr(self.structure, 'agents'):
                self.structure.agents = [agent for agent in self.structure.agents 
                                       if agent.get('agent_id') != node_id]
            
            # 尝试使用结构管理器的remove_agent方法
            if hasattr(self.structure, 'remove_agent'):
                return self.structure.remove_agent(node_id)
            
            self.logger.info(f"节点 {node_id} 删除成功")
            return True
        except Exception as e:
            self.logger.error(f"删除节点失败: {e}")
            return False
    
    def search_nodes(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        搜索节点
        
        Args:
            query: 搜索查询
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 匹配的节点列表
        """
        try:
            all_agents = self.structure.load_all_agents()
            results = []
            
            for agent in all_agents:
                # 检查过滤条件
                match = True
                if filters:
                    for key, value in filters.items():
                        if agent.get(key) != value:
                            match = False
                            break
                
                # 检查查询文本
                if match and query:
                    query_lower = query.lower()
                    agent_info = " ".join(str(v) for v in agent.values()).lower()
                    if query_lower not in agent_info:
                        match = False
                
                if match:
                    results.append(agent)
            
            return results
        except Exception as e:
            self.logger.error(f"搜索节点失败: {e}")
            return []
    
    def get_all_nodes(self) -> List[Dict[str, Any]]:
        """
        获取所有节点
        
        Returns:
            List[Dict[str, Any]]: 所有节点列表
        """
        # 缓存键为'special_all_nodes_key'
        all_nodes_key = 'special_all_nodes_key'
        if all_nodes_key in self.node_cache:
            cached = self.node_cache[all_nodes_key]
            if datetime.now() - cached['timestamp'] < self.cache_ttl:
                return cached['data']
            self.logger.info("所有节点缓存将过期，自动刷新")
        
        try:
            nodes = self.structure.load_all_agents()
            self.node_cache[all_nodes_key] = {
                'data': nodes,
                'timestamp': datetime.now()
            }
            return nodes
        except Exception as e:
            self.logger.error(f"获取所有节点失败: {e}")
            return []
    
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
                # self.logger.info("节点缓存已自动刷新")
        
        # 使用守护线程运行，避免影响主程序退出
        thread = threading.Thread(target=refresh_cache, daemon=True)
        thread.start()
    
    def refresh_cache(self):
        """
        刷新节点缓存
        """
        self.node_cache.clear()
        self.all_nodes_cache = None
        # self.logger.info("节点缓存已刷新")
    
    def close(self):
        """
        关闭服务
        """
        if self.structure:
            self.structure.close()
        self.node_cache.clear()
        self.logger.info("节点服务已关闭")
