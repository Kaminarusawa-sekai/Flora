"""HTTP API适配器"""
import requests
import json
from typing import Dict, Any, Optional
from .api_interface import ApiInterface
from ..adapter_base import AdapterBase


class HttpAdapter(AdapterBase, ApiInterface):
    """
    HTTP API适配器，用于发送HTTP请求与外部API交互
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化HTTP适配器
        
        Args:
            config: 配置参数
                - base_url: 基础URL
                - timeout: 超时时间（秒）
                - headers: 默认请求头
                - auth: 认证信息
        """
        super().__init__(config)
        self.base_url = self.get_config_value('base_url', '')
        self.timeout = self.get_config_value('timeout', 30)
        self.default_headers = self.get_config_value('headers', {})
        self.auth = self.get_config_value('auth', None)
        self.session = requests.Session()
    
    def initialize(self) -> bool:
        """
        初始化适配器
        
        Returns:
            bool: 初始化是否成功
        """
        try:
            # 配置session
            if self.auth:
                self.session.auth = self.auth
            
            # 设置默认headers
            for key, value in self.default_headers.items():
                self.session.headers[key] = value
            
            # 设置默认Content-Type
            if 'Content-Type' not in self.session.headers:
                self.session.headers['Content-Type'] = 'application/json'
            
            self.is_initialized = True
            return True
        except Exception as e:
            print(f"HTTP适配器初始化失败: {e}")
            return False
    
    def close(self) -> None:
        """
        关闭适配器，释放资源
        """
        if hasattr(self, 'session'):
            self.session.close()
        self.is_initialized = False
    
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
        url = self._build_url(endpoint)
        combined_headers = self._combine_headers(headers)
        
        try:
            response = self.session.get(
                url,
                params=params,
                headers=combined_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return self._parse_response(response)
        except requests.RequestException as e:
            print(f"GET请求失败: {e}")
            raise
    
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
        url = self._build_url(endpoint)
        combined_headers = self._combine_headers(headers)
        
        try:
            response = self.session.post(
                url,
                json=data,
                headers=combined_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return self._parse_response(response)
        except requests.RequestException as e:
            print(f"POST请求失败: {e}")
            raise
    
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
        url = self._build_url(endpoint)
        combined_headers = self._combine_headers(headers)
        
        try:
            response = self.session.put(
                url,
                json=data,
                headers=combined_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return self._parse_response(response)
        except requests.RequestException as e:
            print(f"PUT请求失败: {e}")
            raise
    
    def delete(self, endpoint: str, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        发送DELETE请求
        
        Args:
            endpoint: API端点
            headers: 请求头
            
        Returns:
            Dict[str, Any]: 响应数据
        """
        url = self._build_url(endpoint)
        combined_headers = self._combine_headers(headers)
        
        try:
            response = self.session.delete(
                url,
                headers=combined_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return self._parse_response(response)
        except requests.RequestException as e:
            print(f"DELETE请求失败: {e}")
            raise
    
    def set_base_url(self, base_url: str) -> None:
        """
        设置基础URL
        
        Args:
            base_url: 基础URL
        """
        self.base_url = base_url.rstrip('/')
    
    def set_default_headers(self, headers: Dict[str, str]) -> None:
        """
        设置默认请求头
        
        Args:
            headers: 默认请求头
        """
        self.default_headers = headers
        # 更新session的headers
        self.session.headers.clear()
        for key, value in headers.items():
            self.session.headers[key] = value
    
    def set_timeout(self, timeout: int) -> None:
        """
        设置请求超时时间
        
        Args:
            timeout: 超时时间（秒）
        """
        self.timeout = timeout
    
    def _build_url(self, endpoint: str) -> str:
        """
        构建完整的URL
        
        Args:
            endpoint: API端点
            
        Returns:
            str: 完整的URL
        """
        if endpoint.startswith(('http://', 'https://')):
            return endpoint
        
        if self.base_url:
            if endpoint.startswith('/'):
                return f"{self.base_url}{endpoint}"
            else:
                return f"{self.base_url}/{endpoint}"
        
        return endpoint
    
    def _combine_headers(self, headers: Optional[Dict[str, str]]) -> Dict[str, str]:
        """
        合并请求头
        
        Args:
            headers: 自定义请求头
            
        Returns:
            Dict[str, str]: 合并后的请求头
        """
        combined = self.session.headers.copy()
        if headers:
            combined.update(headers)
        return combined
    
    def _parse_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        解析响应数据
        
        Args:
            response: HTTP响应
            
        Returns:
            Dict[str, Any]: 解析后的数据
        """
        try:
            return response.json()
        except json.JSONDecodeError:
            # 如果不是JSON格式，返回文本
            return {'text': response.text}
