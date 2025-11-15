"""
树结构管理模块
提供智能体树结构、节点关系和路径管理功能
"""

from .node_service import (NodeService)

from .relationship_service import (RelationshipService)

from .tree_manager import (TreeManager)

__all__ = [
    # 节点服务
    'NodeService',
    
    # 关系服务
    'RelationshipService',
    
    # 树管理器
    'TreeManager'
]

__version__ = '1.0.0'
__author__ = 'Flora AI Team'
__description__ = '树结构管理模块 - 提供智能体组织结构的管理和维护'
