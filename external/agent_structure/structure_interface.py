"""Agent树形结构管理抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, TYPE_CHECKING

# 避免循环导入
if TYPE_CHECKING:
    import networkx as nx


class AgentStructureInterface(ABC):
    """
    Agent树形结构管理的抽象接口，定义操作Agent层级关系的标准方法
    """
    
    @abstractmethod
    def get_agent_relationship(self, agent_id: str) -> Dict[str, Any]:
        """
        获取指定Agent的父子关系
        
        Args:
            agent_id: Agent唯一标识符
            
        Returns:
            包含父子关系信息的字典，格式为 {'parent': parent_id, 'children': [child_ids]}
        """
        pass
    
    @abstractmethod
    def load_all_agents(self) -> List[Dict[str, Any]]:
        """
        加载所有Agent节点信息
        
        Returns:
            Agent节点信息列表，每个节点包含agent_id和其他元数据
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭连接，释放资源
        """
        pass
    
    @abstractmethod
    def add_agent_relationship(self, parent_id: str, child_id: str, relationship_type: str) -> bool:
        """
        添加Agent间的父子关系
        
        Args:
            parent_id: 父Agent ID
            child_id: 子Agent ID
            relationship_type: 关系类型
            
        Returns:
            是否添加成功
        """
        pass
    
    @abstractmethod
    def remove_agent(self, agent_id: str) -> bool:
        """
        删除指定Agent及其所有关系
        
        Args:
            agent_id: 要删除的Agent ID
            
        Returns:
            是否删除成功
        """
        pass
    
    @abstractmethod
    def create_node(self, node_data: Dict[str, Any]) -> Optional[str]:
        """
        创建新的Agent节点
        
        Args:
            node_data: 节点数据，必须包含agent_id
            
        Returns:
            创建的节点ID，如果创建失败则返回None
        """
        pass
    
    @abstractmethod
    def update_node(self, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新节点信息
        
        Args:
            node_id: 节点ID
            updates: 更新内容
            
        Returns:
            是否更新成功
        """
        pass
    
    def get_agent_by_id(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单个Agent信息
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Agent信息，如果不存在则返回None
        """
        # 默认实现，通过load_all_agents查找
        all_agents = self.load_all_agents()
        for agent in all_agents:
            if agent.get('agent_id') == agent_id:
                return agent
        return None
    
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
        # 默认实现抛出NotImplementedError，由具体实现类提供
        raise NotImplementedError("子类必须实现get_influenced_subgraph方法")
