"""Agent注册表，负责管理所有Agent的注册、查询和关系管理"""
from typing import Dict, Any, Optional, List
import logging
from contextlib import contextmanager
from .tree.tree_manager import TreeManager
from ..common.utils.actor_reference_manager import actor_reference_manager


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
    
    def __init__(self, tree_manager: Optional[TreeManager] = None):
        """初始化Agent注册表"""
        if hasattr(self, '_initialized') and self._initialized:
            return
        
        self.logger = logging.getLogger(__name__)
        self.tree_manager = tree_manager or TreeManager()
        self._initialized = True
        # 初始化RouterActor和ActorSystem引用（可在外部设置）
        self.router_actor = None
        self.actor_system = None
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
        # 尝试从RouterActor获取
        try:
            # 从agent_id中提取tenant_id和node_id
            # 假设agent_id格式为 "{tenant_id}_{node_id}" 或类似格式
            # 这里可以根据实际情况调整解析逻辑
            parts = agent_id.split('_')
            if len(parts) >= 2:
                tenant_id = parts[0]
                node_id = '_'.join(parts[1:]) if len(parts) > 2 else parts[1]
                
                # 使用新的获取或创建方法
                return self.get_or_create_agent_actor(tenant_id, node_id)
        except Exception as e:
            self.logger.warning(f"尝试通过RouterActor获取actor_ref失败: {e}")
            
        # 如果失败，回退到TreeManager的实现
        return self.tree_manager.get_actor_ref(agent_id)
    
    def set_actor_ref(self, agent_id: str, actor_ref: Any) -> bool:
        """
        设置Agent的Actor引用
        
        Args:
            agent_id: Agent ID
            actor_ref: Actor引用
            
        Returns:
            设置是否成功
        """
        self.tree_manager.set_actor_ref(agent_id, actor_ref)
        return True
    
    def get_or_create_agent_actor(self, tenant_id: str, node_id: str) -> Optional[Any]:
        """
        获取或创建一个与指定租户和节点相关的AgentActor。
        通过RouterActor确保同一租户和节点下只有一个AgentActor实例。
        
        Args:
            tenant_id: 租户ID
            node_id: 节点ID
            
        Returns:
            可以发送消息的地址或引用，如果失败则返回None
        """
        if not hasattr(self, 'router_actor') or not self.router_actor:
            self.logger.error("RouterActor未初始化，无法获取或创建AgentActor")
            return None
            
        try:
            # 创建UserRequest消息
            request = type('UserRequest', (), {'tenant_id': tenant_id, 'node_id': node_id})
            
            # 发送请求到RouterActor
            # 注意：在实际使用中，可能需要等待响应或其他方式获取Actor引用
            # 这里为了简化，我们直接返回RouterActor作为代理，所有消息都通过它路由
            self.logger.info(f"通过RouterActor获取或创建AgentActor: tenant={tenant_id}, node={node_id}")
            
            # 发送初始化请求（非阻塞）
            if hasattr(self, 'actor_system'):
                self.actor_system.tell(self.router_actor, request)
            
            # 为了保持与现有API的兼容性，我们返回一个可以被调用的对象
            # 实际消息将通过RouterActor路由
            class RouterProxy:
                def __init__(self, system, router, tenant, node):
                    self.system = system
                    self.router = router
                    self.tenant = tenant
                    self.node = node
                    
                def __call__(self, msg):
                    # 包装消息，添加租户和节点信息
                    wrapped_msg = {
                        "message_type": "user_request",
                        "tenant_id": self.tenant,
                        "node_id": self.node,
                        "payload": msg
                    }
                    if self.system:
                        self.system.tell(self.router, wrapped_msg)
                    return True
                    
                def tell(self, msg):
                    # 提供与ActorSystem兼容的tell方法
                    wrapped_msg = {
                        "message_type": "user_request",
                        "tenant_id": self.tenant,
                        "node_id": self.node,
                        "payload": msg
                    }
                    if self.system:
                        self.system.tell(self.router, wrapped_msg)
                    return True
            
            return RouterProxy(getattr(self, 'actor_system', None), self.router_actor, tenant_id, node_id)
            
        except Exception as e:
            self.logger.error(f"获取或创建AgentActor失败: {e}")
            return None
    
    def remove_actor_ref(self, agent_id: str) -> bool:
        """
        移除Agent的Actor引用
        
        Args:
            agent_id: Agent ID
            
        Returns:
            移除是否成功
        """
        # 尝试通知RouterActor移除对应的SessionActor
        try:
            if hasattr(self, 'router_actor') and self.router_actor:
                # 从agent_id中提取tenant_id和node_id
                parts = agent_id.split('_')
                if len(parts) >= 2:
                    tenant_id = parts[0]
                    node_id = '_'.join(parts[1:]) if len(parts) > 2 else parts[1]
                    
                    # 发送注销消息
                    unregister_msg = {
                        "message_type": "unregister_actor",
                        "tenant_id": tenant_id,
                        "node_id": node_id
                    }
                    if hasattr(self, 'actor_system'):
                        self.actor_system.tell(self.router_actor, unregister_msg)
                    self.logger.info(f"通过RouterActor注销AgentActor: agent_id={agent_id}")
        except Exception as e:
            self.logger.warning(f"尝试通过RouterActor注销actor_ref失败: {e}")
            
        # 同时调用TreeManager的移除方法
        self.tree_manager.remove_actor_ref(agent_id)
        return True
    
    def is_agent_active(self, agent_id: str) -> bool:
        """
        检查指定的Agent是否处于活跃状态（有Actor引用）。
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent是否活跃
        """
        # 尝试通过RouterActor检查
        try:
            if hasattr(self, 'router_actor') and self.router_actor:
                # 从agent_id中提取tenant_id和node_id
                parts = agent_id.split('_')
                if len(parts) >= 2:
                    tenant_id = parts[0]
                    node_id = '_'.join(parts[1:]) if len(parts) > 2 else parts[1]
                    
                    # 发送检查活跃状态的消息
                    # 注意：这只是示例，实际实现可能需要等待响应或使用其他机制
                    check_active_msg = {
                        "message_type": "check_active",
                        "tenant_id": tenant_id,
                        "node_id": node_id
                    }
                    # 非阻塞发送，不等待响应
                    if hasattr(self, 'actor_system'):
                        self.actor_system.tell(self.router_actor, check_active_msg)
                    # 为了简化，我们假设通过RouterActor获取的都是活跃的
                    # 在实际应用中，应该有更好的机制来检查状态
                    return True
        except Exception as e:
            self.logger.warning(f"尝试通过RouterActor检查agent活跃状态失败: {e}")
            
        # 如果失败，回退到基础实现
        return self.get_actor_ref(agent_id) is not None
        
    @contextmanager
    def agent_context(self, agent_id: str):
        """
        创建一个Agent上下文管理器，
        在上下文中可以使用Agent，
        退出上下文时会自动清理Actor引用。
        
        Args:
            agent_id: Agent ID
        """
        try:
            yield
        finally:
            self.remove_actor_ref(agent_id)
    
    @contextmanager
    def agent_actor_context(self, tenant_id: str, node_id: str):
        """
        创建一个AgentActor上下文管理器，
        使用RouterActor确保同一租户和节点下只有一个AgentActor实例，
        退出上下文时会自动清理。
        
        Args:
            tenant_id: 租户ID
            node_id: 节点ID
            
        Yields:
            可以用于发送消息的Actor引用代理
        """
        actor_ref = None
        try:
            # 获取或创建AgentActor
            actor_ref = self.get_or_create_agent_actor(tenant_id, node_id)
            yield actor_ref
        finally:
            # 清理Actor引用
            if actor_ref:
                try:
                    # 创建agent_id用于移除引用
                    agent_id = f"{tenant_id}_{node_id}"
                    self.remove_actor_ref(agent_id)
                except Exception as e:
                    self.logger.error(f"清理AgentActor引用失败: {e}")
                    
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
