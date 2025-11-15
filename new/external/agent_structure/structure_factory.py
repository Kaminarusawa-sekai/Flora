"""Agent结构管理器工厂类"""
from typing import Dict, Any
from .neo4j_structure import Neo4JAgentStructure


def create_agent_structure(config: Dict[str, Any]):
    """
    工厂方法创建Agent结构管理器
    
    Args:
        config: 配置字典，包含结构类型和相关参数
        
    Returns:
        AgentStructureInterface: Agent结构管理器实例
        
    Raises:
        ValueError: 当指定的结构类型不支持时
    """
    structure_type = config.get('type', 'neo4j')
    
    if structure_type == 'neo4j':
        # 验证Neo4j配置是否完整
        required_keys = ['uri', 'user', 'password']
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing Neo4j configuration key: {key}")
        
        return Neo4JAgentStructure(
            uri=config['uri'],
            user=config['user'],
            password=config['password']
        )
    else:
        raise ValueError(f"Unsupported agent structure type: {structure_type}")
