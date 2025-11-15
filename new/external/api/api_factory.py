"""API适配器工厂"""
from typing import Dict, Any
from .api_interface import ApiInterface
from .http_adapter import HttpAdapter


def create_api_adapter(api_type: str, config: Dict[str, Any] = None) -> ApiInterface:
    """
    工厂方法，根据API类型创建对应的API适配器
    
    Args:
        api_type: API类型
            - 'http': HTTP/HTTPS API
        config: 配置参数
        
    Returns:
        ApiInterface: API适配器实例
        
    Raises:
        ValueError: 当API类型不支持时
    """
    
    api_type = api_type.lower()
    
    if api_type == 'http':
        adapter = HttpAdapter(config or {})
    else:
        raise ValueError(f"不支持的API类型: {api_type}")
    
    # 初始化适配器
    if not adapter.initialize():
        raise RuntimeError(f"{api_type} API适配器初始化失败")
    
    return adapter


def get_api_adapter_types() -> list:
    """
    获取支持的API适配器类型列表
    
    Returns:
        list: 支持的API类型列表
    """
    return ['http']
