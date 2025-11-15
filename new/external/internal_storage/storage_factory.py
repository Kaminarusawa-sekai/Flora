"""内部存储管理器工厂类"""
from typing import Dict, Any
from .sqlite_storage import SQLiteInternalStorage


def create_internal_storage(config: Dict[str, Any]):
    """
    工厂方法创建内部存储管理器
    
    Args:
        config: 配置字典，包含存储类型和相关参数
        
    Returns:
        InternalStorageInterface: 内部存储管理器实例
        
    Raises:
        ValueError: 当指定的存储类型不支持时
    """
    storage_type = config.get('type', 'sqlite')
    
    if storage_type == 'sqlite':
        # 验证SQLite配置是否完整
        if 'db_path' not in config:
            raise ValueError("Missing SQLite configuration key: db_path")
        
        return SQLiteInternalStorage(db_path=config['db_path'])
    else:
        raise ValueError(f"Unsupported internal storage type: {storage_type}")
