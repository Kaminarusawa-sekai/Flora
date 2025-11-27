"""数据访问抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from .tree_model import TreeNode


class DataAccessInterface(ABC):
    """
    数据访问抽象接口，定义统一的数据操作方法
    """
    
    @abstractmethod
    def query(self, query_str: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行查询操作
        
        Args:
            query_str: 查询语句
            params: 查询参数
            
        Returns:
            List[Dict[str, Any]]: 查询结果列表
        """
        pass
    
    @abstractmethod
    def get_data_by_id(self, data_id: str, data_type: str) -> Dict[str, Any]:
        """
        根据ID获取数据
        
        Args:
            data_id: 数据ID
            data_type: 数据类型
            
        Returns:
            Dict[str, Any]: 数据对象
        """
        pass
    
    @abstractmethod
    def update_data(self, data_id: str, data_type: str, updates: Dict[str, Any]) -> bool:
        """
        更新数据
        
        Args:
            data_id: 数据ID
            data_type: 数据类型
            updates: 更新内容
            
        Returns:
            bool: 更新是否成功
        """
        pass
    
    @abstractmethod
    def create_data(self, data_type: str, data: Dict[str, Any]) -> str:
        """
        创建数据
        
        Args:
            data_type: 数据类型
            data: 数据内容
            
        Returns:
            str: 创建的数据ID
        """
        pass
    
    @abstractmethod
    def delete_data(self, data_id: str, data_type: str) -> bool:
        """
        删除数据
        
        Args:
            data_id: 数据ID
            data_type: 数据类型
            
        Returns:
            bool: 删除是否成功
        """
        pass
    
    @abstractmethod
    def get_schema(self, data_type: str) -> Dict[str, Any]:
        """
        获取数据类型的模式定义
        
        Args:
            data_type: 数据类型
            
        Returns:
            Dict[str, Any]: 模式定义
        """
        pass
    
    # 树形结构相关方法（可选实现）
    
    def create_tree_node(self, tree_name: str, node: TreeNode) -> str:
        """
        创建树节点
        
        Args:
            tree_name: 树名称
            node: 节点对象
            
        Returns:
            str: 创建的节点ID
        """
        raise NotImplementedError("Tree operations not implemented")
    
    def get_tree_node(self, tree_name: str, node_id: str) -> Optional[TreeNode]:
        """
        获取树节点
        
        Args:
            tree_name: 树名称
            node_id: 节点ID
            
        Returns:
            Optional[TreeNode]: 节点对象
        """
        raise NotImplementedError("Tree operations not implemented")
    
    def update_tree_node(self, tree_name: str, node_id: str, updates: Dict[str, Any]) -> bool:
        """
        更新树节点
        
        Args:
            tree_name: 树名称
            node_id: 节点ID
            updates: 更新内容
            
        Returns:
            bool: 更新是否成功
        """
        raise NotImplementedError("Tree operations not implemented")
    
    def delete_tree_node(self, tree_name: str, node_id: str, cascade: bool = False) -> bool:
        """
        删除树节点
        
        Args:
            tree_name: 树名称
            node_id: 节点ID
            cascade: 是否级联删除
            
        Returns:
            bool: 删除是否成功
        """
        raise NotImplementedError("Tree operations not implemented")
    
    def get_tree_children(self, tree_name: str, parent_id: Optional[str] = None) -> List[TreeNode]:
        """
        获取树节点的子节点
        
        Args:
            tree_name: 树名称
            parent_id: 父节点ID，None表示获取根节点
            
        Returns:
            List[TreeNode]: 子节点列表
        """
        raise NotImplementedError("Tree operations not implemented")
    
    def get_tree_path(self, tree_name: str, node_id: str) -> List[TreeNode]:
        """
        获取从根节点到指定节点的路径
        
        Args:
            tree_name: 树名称
            node_id: 节点ID
            
        Returns:
            List[TreeNode]: 路径节点列表
        """
        raise NotImplementedError("Tree operations not implemented")
    
    def move_tree_node(self, tree_name: str, node_id: str, new_parent_id: Optional[str], 
                      order: int = -1) -> bool:
        """
        移动树节点
        
        Args:
            tree_name: 树名称
            node_id: 节点ID
            new_parent_id: 新父节点ID
            order: 排序位置
            
        Returns:
            bool: 移动是否成功
        """
        raise NotImplementedError("Tree operations not implemented")
