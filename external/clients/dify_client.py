"""Dify API客户端"""
from typing import Dict, Any, Optional
from .http_client import HttpClient


class DifyClient:
    """
    Dify API客户端，负责与Dify API进行交互
    """
    
    def __init__(self, api_key: str, base_url: str = "https://api.dify.ai/v1"):
        """
        初始化Dify客户端
        
        Args:
            api_key: Dify API密钥
            base_url: Dify API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url
        self.http_client = HttpClient()
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def run_workflow(self, inputs: Dict[str, Any], app_id: str, query: Optional[str] = None) -> Dict[str, Any]:
        """
        运行Dify工作流
        
        Args:
            inputs: 工作流输入参数
            app_id: Dify应用ID
            query: 用户查询（可选）
            
        Returns:
            执行结果
        """
        payload = {
            'query': query or '',
            'inputs': inputs
        }
        
        url = f"{self.base_url}/chat-messages"
        response = self.http_client.post(url, json=payload, headers=self.headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                'error': f'Request failed with status {response.status_code}',
                'details': response.text
            }
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            连接是否健康
        """
        url = f"{self.base_url}/status"
        response = self.http_client.get(url, headers=self.headers)
        return response.status_code == 200
    
    def close(self) -> None:
        """
        关闭HTTP客户端
        """
        self.http_client.close()
