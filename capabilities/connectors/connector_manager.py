from typing import Dict, Any, Optional
from external.clients import HttpClient, DifyClient

class UniversalConnectorManager:
    """
    通用连接器管理器，负责管理和执行各种外部连接器操作
    从 UniversalConnectorOrchestrator 迁移而来，去掉了 Thespian 依赖
    现在直接使用 external/clients 下的客户端
    """
    
    def __init__(self):
        """初始化连接器管理器"""
        # 客户端缓存，避免重复创建
        self._client_cache = {}
    
    def execute(self, connector_name: str, operation_name: str = "execute", inputs: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行连接器操作
        
        Args:
            connector_name: 连接器名称
            operation_name: 操作名称（默认：execute）
            inputs: 输入参数
            params: 配置参数
            
        Returns:
            Dict[str, Any]: 执行结果
            
        Raises:
            Exception: 执行失败时抛出异常
        """
        if inputs is None:
            inputs = {}
        if params is None:
            params = {}
        
        try:
            # 根据连接器名称选择对应的客户端
            if connector_name.lower() == "dify":
                result = self._execute_dify(operation_name, inputs, params)
            elif connector_name.lower() == "http":
                result = self._execute_http(operation_name, inputs, params)
            else:
                raise Exception(f"Unsupported connector: {connector_name}")
            
            return {
                "status": "SUCCESS",
                "result": result,
                "connector_name": connector_name
            }
        except Exception as e:
            raise Exception(f"Connector execution failed: {str(e)}")
    
    def _execute_dify(self, operation_name: str, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行Dify连接器操作
        
        Args:
            operation_name: 操作名称
            inputs: 输入参数
            params: 配置参数
            
        Returns:
            执行结果
        """
        # 获取Dify配置
        api_key = params.get("api_key")
        base_url = params.get("base_url", "https://api.dify.ai/v1")
        app_id = params.get("app_id")
        
        if not api_key:
            raise Exception("Dify API key is required")
        
        if not app_id:
            raise Exception("Dify app_id is required")
        
        # 创建或获取Dify客户端
        client_key = f"dify_{api_key[:8]}_{base_url}"
        if client_key not in self._client_cache:
            self._client_cache[client_key] = DifyClient(api_key, base_url)
        
        dify_client = self._client_cache[client_key]
        
        # 根据操作名称执行不同的操作
        if operation_name == "execute":
            # 执行Dify工作流
            query = params.get("query")
            return dify_client.run_workflow(inputs, app_id, query)
        else:
            raise Exception(f"Unsupported operation for Dify connector: {operation_name}")
    
    def _execute_http(self, operation_name: str, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行HTTP连接器操作
        
        Args:
            operation_name: 操作名称
            inputs: 输入参数
            params: 配置参数
            
        Returns:
            执行结果
        """
        # 获取HTTP配置
        url = params.get("url")
        method = params.get("method", "POST")
        headers = params.get("headers", {})
        
        if not url:
            raise Exception("HTTP URL is required")
        
        # 创建HTTP客户端
        http_client = HttpClient()
        
        try:
            # 根据HTTP方法执行请求
            if operation_name == "execute":
                if method.upper() == "GET":
                    response = http_client.get(url, params=inputs, headers=headers)
                elif method.upper() == "POST":
                    response = http_client.post(url, json=inputs, headers=headers)
                elif method.upper() == "PUT":
                    response = http_client.put(url, json=inputs, headers=headers)
                elif method.upper() == "DELETE":
                    response = http_client.delete(url, headers=headers)
                else:
                    raise Exception(f"Unsupported HTTP method: {method}")
                
                # 处理响应
                if response.status_code in [200, 201, 202, 204]:
                    try:
                        return response.json()
                    except ValueError:
                        return {"response": response.text}
                else:
                    return {
                        "error": f"HTTP request failed with status {response.status_code}",
                        "details": response.text
                    }
            else:
                raise Exception(f"Unsupported operation for HTTP connector: {operation_name}")
        finally:
            # 关闭HTTP客户端
            http_client.close()
    
    def health_check(self, connector_name: str, params: Dict[str, Any]) -> bool:
        """
        执行健康检查
        
        Args:
            connector_name: 连接器名称
            params: 配置参数
            
        Returns:
            健康检查结果
        """
        if connector_name.lower() == "dify":
            api_key = params.get("api_key")
            base_url = params.get("base_url", "https://api.dify.ai/v1")
            
            if not api_key:
                return False
            
            client = DifyClient(api_key, base_url)
            return client.health_check()
        elif connector_name.lower() == "http":
            url = params.get("url")
            
            if not url:
                return False
            
            client = HttpClient()
            try:
                response = client.get(url)
                return response.status_code in [200, 201, 202, 204]
            finally:
                client.close()
        else:
            return False
