# vanna_factory.py

from typing import Dict, Any
from capabilities.text_to_sql.vanna.ivanna_service import IVannaService

# 注册表：映射名称到构造函数
_VANNA_REGISTRY: Dict[str, type] = {}

def register_vanna(name: str):
    """装饰器：用于注册 Vanna 实现类"""
    def decorator(cls: type):
        if not issubclass(cls, IVannaService):
            raise TypeError(f"{cls.__name__} must implement IVannaService")
        _VANNA_REGISTRY[name] = cls
        return cls
    return decorator

class VannaFactory:
    @staticmethod
    def create(vanna_type: str, business_id: str, **kwargs) -> IVannaService:
        if vanna_type not in _VANNA_REGISTRY:
            raise ValueError(f"Unknown vanna type: {vanna_type}. Available: {list(_VANNA_REGISTRY.keys())}")
        cls = _VANNA_REGISTRY[vanna_type]
        return cls(business_id=business_id, **kwargs)

    @staticmethod
    def list_available() -> list:
        return list(_VANNA_REGISTRY.keys())