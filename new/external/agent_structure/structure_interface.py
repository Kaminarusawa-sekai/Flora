"""Agent树形结构管理抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any


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
            包含父子关系信息的字典
        """
        pass
    
    @abstractmethod
    def load_all_agents(self) -> List[Dict[str, Any]]:
        """
        加载所有Agent节点信息
        
        Returns:
            Agent节点信息列表
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
