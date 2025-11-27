"""API适配器抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Union


class ApiInterface(ABC):
    """
    API适配器抽象接口，定义与外部API交互的通用方法
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化API适配器
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭适配器，释放资源
        """
        pass
    
    @abstractmethod
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        发送GET请求
        
        Args:
            endpoint: API端点
            params: URL参数
            headers: 请求头
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        pass
    
    @abstractmethod
    def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        发送POST请求
        
        Args:
            endpoint: API端点
            data: 请求体数据
            headers: 请求头
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        pass
    
    @abstractmethod
    def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        发送PUT请求
        
        Args:
            endpoint: API端点
            data: 请求体数据
            headers: 请求头
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        pass
    
    @abstractmethod
    def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        发送DELETE请求
        
        Args:
            endpoint: API端点
            headers: 请求头
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        pass
    
    @abstractmethod
    def set_base_url(self, base_url: str) -> None:
        """
        设置基础URL
        
        Args:
            base_url: 基础URL
        """
        pass
    
    @abstractmethod
    def set_default_headers(self, headers: Dict[str, str]) -> None:
        """
        设置默认请求头
        
        Args:
            headers: 默认请求头
        """
        pass
    
    @abstractmethod
    def set_timeout(self, timeout: int) -> None:
        """
        设置请求超时时间
        
        Args:
            timeout: 超时时间（秒）
        """
        pass
