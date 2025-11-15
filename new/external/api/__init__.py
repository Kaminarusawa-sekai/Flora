"""API适配器模块"""

from .api_interface import ApiInterface
from .http_adapter import HttpAdapter
from .api_factory import create_api_adapter

__all__ = [
    'ApiInterface',
    'HttpAdapter',
    'create_api_adapter'
]
