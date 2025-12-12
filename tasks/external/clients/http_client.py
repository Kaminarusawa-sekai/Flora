"""通用HTTP客户端，带有重试机制"""
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any, Optional


class HttpClient:
    """
    通用HTTP客户端，带有重试机制
    """
    
    def __init__(self, retry_count: int = 3, backoff_factor: float = 0.5):
        """
        初始化HTTP客户端
        
        Args:
            retry_count: 重试次数
            backoff_factor: 重试退避因子
        """
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=retry_count,
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=backoff_factor,
            allowed_methods=["HEAD", "GET", "PUT", "DELETE", "OPTIONS", "TRACE", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def get(self, url: str, params: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        发送GET请求
        
        Args:
            url: 请求URL
            params: 查询参数
            headers: 请求头
            
        Returns:
            requests.Response: 响应对象
        """
        return self.session.get(url, params=params, headers=headers)
    
    def post(self, url: str, json: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        发送POST请求
        
        Args:
            url: 请求URL
            json: JSON请求体
            data: 表单数据
            headers: 请求头
            
        Returns:
            requests.Response: 响应对象
        """
        return self.session.post(url, json=json, data=data, headers=headers)
    
    def put(self, url: str, json: Optional[Dict[str, Any]] = None, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        发送PUT请求
        
        Args:
            url: 请求URL
            json: JSON请求体
            headers: 请求头
            
        Returns:
            requests.Response: 响应对象
        """
        return self.session.put(url, json=json, headers=headers)
    
    def delete(self, url: str, headers: Optional[Dict[str, str]] = None) -> requests.Response:
        """
        发送DELETE请求
        
        Args:
            url: 请求URL
            headers: 请求头
            
        Returns:
            requests.Response: 响应对象
        """
        return self.session.delete(url, headers=headers)
    
    def close(self) -> None:
        """
        关闭HTTP会话
        """
        self.session.close()
