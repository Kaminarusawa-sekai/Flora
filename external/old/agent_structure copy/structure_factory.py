"""Agent结构管理器工厂类"""
from typing import Dict, Any, Optional
from .structure_interface import AgentStructureInterface
from .neo4j_structure import Neo4JAgentStructure, MemoryAgentStructure


def create_agent_structure(config: Optional[Dict[str, Any]] = None) -> AgentStructureInterface:
    """
    创建Agent结构管理器实例
    
    Args:
        config: 配置字典，包含结构类型和相关参数
        
    Returns:
        AgentStructureInterface实例
        
    Raises:
        ValueError: 当指定的结构类型不支持时
    """
    # 默认配置
    default_config = {
        'type': 'neo4j',
        'uri': 'neo4j://localhost:7687',
        'user': 'neo4j',
        'password': 'neo4j'
    }
    
    # 如果提供了配置，合并默认配置
    if config:
        default_config.update(config)
    
    structure_type = default_config.get('type')
    
    if structure_type == 'neo4j':
        # 验证Neo4j配置是否完整
        required_keys = ['uri', 'user', 'password']
        for key in required_keys:
            if key not in default_config:
                raise ValueError(f"Neo4j配置缺少必要参数: {key}")
        
        # 创建Neo4j结构管理器
        return Neo4JAgentStructure(
            uri=default_config['uri'],
            user=default_config['user'],
            password=default_config['password']
        )
    elif structure_type == 'memory':
        # 创建内存存储结构管理器
        return MemoryAgentStructure()
    else:
        raise ValueError(f"不支持的结构类型: {structure_type}")
