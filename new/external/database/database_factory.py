"""数据库适配器工厂"""
from typing import Dict, Any
from .database_interface import DatabaseInterface
from .mysql_adapter import MySQLAdapter
from .neo4j_adapter import Neo4jAdapter


def create_database_adapter(db_type: str, config: Dict[str, Any]) -> DatabaseInterface:
    """
    工厂方法，根据数据库类型创建对应的数据库适配器
    
    Args:
        db_type: 数据库类型
            - 'mysql': MySQL数据库
            - 'neo4j': Neo4j图数据库
        config: 数据库配置参数
        
    Returns:
        DatabaseInterface: 数据库适配器实例
        
    Raises:
        ValueError: 当数据库类型不支持时
    """
    
    db_type = db_type.lower()
    
    if db_type == 'mysql':
        adapter = MySQLAdapter(config)
    elif db_type == 'neo4j':
        adapter = Neo4jAdapter(config)
    else:
        raise ValueError(f"不支持的数据库类型: {db_type}")
    
    # 初始化适配器
    if not adapter.initialize():
        raise RuntimeError(f"{db_type}数据库适配器初始化失败")
    
    return adapter


def get_database_adapter_types() -> list:
    """
    获取支持的数据库适配器类型列表
    
    Returns:
        list: 支持的数据库类型列表
    """
    return ['mysql', 'neo4j']
