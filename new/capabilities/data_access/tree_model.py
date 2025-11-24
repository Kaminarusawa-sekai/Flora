"""树形结构模型"""
from typing import Dict, Any, List, Optional


class TreeNode:
    """
    树形结构节点模型
    """
    
    def __init__(self, node_id: str, name: str, parent_id: Optional[str] = None,
                 data: Dict[str, Any] = None, children: List['TreeNode'] = None):
        """
        初始化树形节点
        
        Args:
            node_id: 节点ID
            name: 节点名称
            parent_id: 父节点ID
            data: 节点数据
            children: 子节点列表
        """
        self.node_id = node_id
        self.name = name
        self.parent_id = parent_id
        self.data = data or {}
        self.children = children or []
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            Dict[str, Any]: 节点的字典表示
        """
        return {
            'node_id': self.node_id,
            'name': self.name,
            'parent_id': self.parent_id,
            'data': self.data,
            'children': [child.to_dict() for child in self.children]
        }
    
    @classmethod
    def from_dict(cls, node_dict: Dict[str, Any]) -> 'TreeNode':
        """
        从字典创建TreeNode实例
        
        Args:
            node_dict: 节点的字典表示
            
        Returns:
            TreeNode: TreeNode实例
        """
        children = []
        if 'children' in node_dict:
            for child_dict in node_dict['children']:
                children.append(cls.from_dict(child_dict))
        
        return cls(
            node_id=node_dict['node_id'],
            name=node_dict['name'],
            parent_id=node_dict.get('parent_id'),
            data=node_dict.get('data', {}),
            children=children
        )
    
    def add_child(self, child: 'TreeNode') -> None:
        """
        添加子节点
        
        Args:
            child: 子节点
        """
        self.children.append(child)
    
    def remove_child(self, node_id: str) -> bool:
        """
        删除指定ID的子节点
        
        Args:
            node_id: 子节点ID
            
        Returns:
            bool: 是否成功删除
        """
        for i, child in enumerate(self.children):
            if child.node_id == node_id:
                del self.children[i]
                return True
        return False
    
    def find_child(self, node_id: str) -> Optional['TreeNode']:
        """
        查找指定ID的子节点
        
        Args:
            node_id: 子节点ID
            
        Returns:
            Optional[TreeNode]: 找到的子节点或None
        """
        for child in self.children:
            if child.node_id == node_id:
                return child
            # 递归查找子节点
            found = child.find_child(node_id)
            if found:
                return found
        return None
