from typing import Dict, Any, List
from ....external.clients import HttpClient
from .base_connector import BaseConnector


class HttpConnector(BaseConnector):
    """
    HTTP连接器实现
    """
    
    def __init__(self):
        super().__init__()
    
    def _check_missing_config_params(self, params: Dict[str, Any]) -> List[str]:
        """
        检查HTTP连接器缺失的配置参数
        """
        required_params = ["url"]
        missing = []
        for param in required_params:
            if param not in params or params[param] is None or params[param] == "":
                missing.append(param)
        return missing
    
    def _get_required_params(self) -> List[str]:
        """
        获取HTTP必需配置参数列表
        """
        return ["url"]
    
    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行HTTP连接器操作
        """
        # 1. 检查配置参数 - 直接报错，不返回NEED_INPUT
        missing_config_params = self._check_missing_config_params(params)
        
        if missing_config_params:
            raise Exception(f"Missing required config parameters: {', '.join(missing_config_params)}")
        
        # 2. 检查输入参数（HTTP连接器通常不需要特定的输入参数）
        missing_inputs = self._check_missing_inputs(inputs)
        if missing_inputs:
            return {
                "status": "NEED_INPUT",
                "missing": missing_inputs,
                "tool_schema": self._get_required_inputs()
            }
        
        # 获取HTTP配置
        url = params["url"]
        method = params.get("method", "GET").upper()
        headers = params.get("headers", {})
        data = params.get("data", inputs)
        timeout = params.get("timeout", 30)
        
        # 创建HTTP客户端
        http_client = HttpClient()
        
        try:
            # 根据HTTP方法执行请求
            if method == "GET":
                response = http_client.get(url, params=data, headers=headers, timeout=timeout)
            elif method == "POST":
                response = http_client.post(url, json=data, headers=headers, timeout=timeout)
            elif method == "PUT":
                response = http_client.put(url, json=data, headers=headers, timeout=timeout)
            elif method == "DELETE":
                response = http_client.delete(url, headers=headers, timeout=timeout)
            else:
                raise Exception(f"Unsupported HTTP method: {method}")
            
            # 处理响应
            if response.status_code in [200, 201, 202, 204]:
                try:
                    return response.json()
                except ValueError:
                    return {"text": response.text, "status_code": response.status_code}
            else:
                return {
                    "error": f"HTTP request failed with status {response.status_code}",
                    "details": response.text
                }
        finally:
            # 关闭HTTP客户端
            http_client.close()
    
    def health_check(self, params: Dict[str, Any]) -> bool:
        """
        执行HTTP健康检查
        """
        url = params.get("url")
        
        if not url:
            return False
        
        client = HttpClient()
        try:
            response = client.get(url)
            return response.status_code in [200, 201, 202, 204]
        finally:
            client.close()
