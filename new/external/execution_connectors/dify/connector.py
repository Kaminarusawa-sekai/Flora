"""Dify连接器实现"""
import requests
from typing import Dict, Any, Optional
from ..base_connector import BaseConnector


class DifyConnector(BaseConnector):
    """
    Dify执行连接器，用于与Dify API进行交互
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Dify连接器
        
        Args:
            config: Dify配置信息
        """
        self.config = config
        self.api_key = config.get('api_key')
        self.base_url = config.get('base_url', 'https://api.dify.ai/v1')
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        self.is_initialized = False
    
    def initialize(self) -> bool:
        """
        初始化连接器
        
        Returns:
            是否初始化成功
        """
        try:
            # 验证配置
            if not self.api_key:
                return False
            
            # 进行健康检查
            if self.health_check():
                self.is_initialized = True
                return True
            return False
        except Exception:
            return False
    
    def execute(self, instruction: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行Dify指令
        
        Args:
            instruction: 执行指令
            params: 执行参数
            
        Returns:
            执行结果
        """
        try:
            # 构建请求参数
            payload = {
                'query': instruction,
                'inputs': params or {}
            }
            
            # 获取应用ID
            app_id = self.config.get('app_id')
            if not app_id:
                return {'error': 'Missing app_id in config'}
            
            # 发送请求
            url = f"{self.base_url}/chat-messages"
            response = requests.post(
                url,
                json=payload,
                headers=self.headers
            )
            
            # 处理响应
            if response.status_code == 200:
                return response.json()
            else:
                return {
                    'error': f'Request failed with status {response.status_code}',
                    'details': response.text
                }
        except Exception as e:
            return {'error': str(e)}
    
    def close(self) -> None:
        """
        关闭连接器
        """
        # Dify API是无状态的，这里不需要特殊的关闭操作
        self.is_initialized = False
    
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            连接是否健康
        """
        try:
            # 发送简单的健康检查请求
            url = f"{self.base_url}/status"
            response = requests.get(url, headers=self.headers)
            return response.status_code == 200
        except Exception:
            return False
