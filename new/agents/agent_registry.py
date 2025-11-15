"""Agent注册表，负责管理所有Agent的注册、查询和关系管理"""
from typing import Dict, Any, Optional, List
import logging
from .tree.tree_manager import TreeManager


class AgentRegistry:
    """
    Agent注册表
    封装TreeManager功能，提供与原有AgentRegistry兼容的接口
    负责Agent的注册、查询、关系管理等功能
    """
    
    # 单例实例
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        """实现单例模式"""
        if not cls._instance:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """初始化Agent注册表"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.logger = logging.getLogger(__name__)
        self.tree_manager = TreeManager()
        self._initialized = True
        self.logger.info("AgentRegistry初始化成功")
    
    def get_agent_meta(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent元数据
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Dict[str, Any]: Agent元数据
        """
        return self.tree_manager.get_agent_meta(agent_id)
    
    def get_children(self, agent_id: str) -> List[str]:
        """
        获取Agent的子节点
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List[str]: 子节点ID列表
        """
        return self.tree_manager.get_children(agent_id)
    
    def get_parent(self, agent_id: str) -> Optional[str]:
        """
        获取Agent的父节点
        
        Args:
            agent_id: Agent ID
            
        Returns:
            str: 父节点ID
        """
        return self.tree_manager.get_parent(agent_id)
    
    def register_agent(self, agent_id: str, agent_meta: Dict[str, Any]) -> bool:
        """
        注册新Agent
        
        Args:
            agent_id: Agent ID
            agent_meta: Agent元数据
            
        Returns:
            bool: 是否注册成功
        """
        try:
            # 确保agent_id在agent_meta中
            agent_meta['agent_id'] = agent_id
            
            # 获取父节点信息
            parent_id = agent_meta.pop('parent_id', None)
            
            # 添加Agent
            result = self.tree_manager.add_agent(agent_meta, parent_id)
            return result is not None
        except Exception as e:
            self.logger.error(f"注册Agent失败: {e}")
            return False
    
    def unregister_agent(self, agent_id: str) -> bool:
        """
        注销Agent
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否注销成功
        """
        return self.tree_manager.delete_agent(agent_id)
    
    def update_agent_meta(self, agent_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新Agent元数据
        
        Args:
            agent_id: Agent ID
            updates: 更新内容
            
        Returns:
            bool: 是否更新成功
        """
        return self.tree_manager.update_agent(agent_id, updates)
    
    def get_root_agents(self) -> List[str]:
        """
        获取所有根节点Agent
        
        Returns:
            List[str]: 根节点Agent ID列表
        """
        return self.tree_manager.get_root_agents()
    
    def get_all_agents(self) -> List[Dict[str, Any]]:
        """
        获取所有Agent
        
        Returns:
            List[Dict[str, Any]]: 所有Agent信息列表
        """
        root_agents = self.get_root_agents()
        all_agents = []
        
        def _collect_agents(agent_id: str):
            meta = self.get_agent_meta(agent_id)
            if meta:
                meta['parent_id'] = self.get_parent(agent_id)
                all_agents.append(meta)
                # 递归收集子节点
                for child_id in self.get_children(agent_id):
                    _collect_agents(child_id)
        
        for root_id in root_agents:
            _collect_agents(root_id)
        
        return all_agents
    
    def is_leaf_agent(self, agent_id: str) -> bool:
        """
        检查Agent是否是叶子节点
        
        Args:
            agent_id: Agent ID
            
        Returns:
            bool: 是否是叶子节点
        """
        return self.tree_manager.is_leaf_agent(agent_id)
    
    def get_full_path(self, agent_id: str) -> List[str]:
        """
        获取Agent的完整路径
        
        Args:
            agent_id: Agent ID
            
        Returns:
            List[str]: 路径节点ID列表
        """
        return self.tree_manager.get_full_path(agent_id)
    
    def find_agent_by_path(self, path: List[str]) -> Optional[str]:
        """
        根据路径查找Agent
        
        Args:
            path: 路径节点ID列表
            
        Returns:
            str: 找到的Agent ID
        """
        return self.tree_manager.find_agent_by_path(path)
    
    def get_subtree(self, root_id: str) -> Dict[str, Any]:
        """
        获取以指定节点为根的子树
        
        Args:
            root_id: 根节点ID
            
        Returns:
            Dict[str, Any]: 子树结构
        """
        return self.tree_manager.get_subtree(root_id)
    
    def search_agents(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        搜索Agent
        
        Args:
            query: 搜索查询
            filters: 过滤条件
            
        Returns:
            List[Dict[str, Any]]: 匹配的Agent列表
        """
        return self.tree_manager.search_agents(query, filters)
    
    def get_agent_depth(self, agent_id: str) -> int:
        """
        获取Agent的深度
        
        Args:
            agent_id: Agent ID
            
        Returns:
            int: 深度
        """
        return self.tree_manager.get_agent_depth(agent_id)
    
    def get_level_agents(self, level: int) -> List[str]:
        """
        获取指定层级的所有Agent
        
        Args:
            level: 层级
            
        Returns:
            List[str]: Agent ID列表
        """
        return self.tree_manager.get_level_agents(level)
    
    def add_agent_relationship(self, parent_id: str, child_id: str) -> bool:
        """
        添加Agent间的关系
        
        Args:
            parent_id: 父Agent ID
            child_id: 子Agent ID
            
        Returns:
            bool: 是否添加成功
        """
        return self.tree_manager.relationship_service.add_relationship(parent_id, child_id)
    
    def remove_agent_relationship(self, parent_id: str, child_id: str) -> bool:
        """
        移除Agent间的关系
        
        Args:
            parent_id: 父Agent ID
            child_id: 子Agent ID
            
        Returns:
            bool: 是否移除成功
        """
        return self.tree_manager.relationship_service.remove_relationship(parent_id, child_id)
    
    def get_actor_ref(self, agent_id: str) -> Optional[Any]:
        """
        获取Agent的Actor引用
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Any: Actor引用
        """
        return self.tree_manager.get_actor_ref(agent_id)
    
    def set_actor_ref(self, agent_id: str, actor_ref: Any) -> None:
        """
        设置Agent的Actor引用
        
        Args:
            agent_id: Agent ID
            actor_ref: Actor引用
        """
        self.tree_manager.set_actor_ref(agent_id, actor_ref)
    
    def remove_actor_ref(self, agent_id: str) -> None:
        """
        移除Agent的Actor引用
        
        Args:
            agent_id: Agent ID
        """
        self.tree_manager.remove_actor_ref(agent_id)
    
    def refresh(self):
        """
        刷新所有缓存
        """
        self.tree_manager.refresh()
    
    def close(self):
        """
        关闭Agent注册表
        """
        if hasattr(self, 'tree_manager'):
            self.tree_manager.close()
        self._initialized = False
        self.logger.info("AgentRegistry已关闭")


# 创建全局AgentRegistry实例
agent_registry = AgentRegistry()
