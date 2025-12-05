from typing import Dict, Any
from .base_excution import BaseExecution
from .connect.dify_connector import DifyConnector
from .connect.http_connector import HttpConnector


class UniversalExecution(BaseExecution):
    """
    通用连接器管理器，负责管理和执行各种外部连接器操作
    从 UniversalConnectorOrchestrator 迁移而来，去掉了 Thespian 依赖
    现在直接使用 external/clients 下的客户端
    """
    
    def __init__(self):
        """初始化连接器管理器"""
        # 连接器实例缓存
        self._connector_cache = {
            "dify": DifyConnector(),
            "dify_workflow": DifyConnector(),
            "http": HttpConnector(),
        }
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        config 示例: 
        {
            "dify": { "base_url": "http://my-dify-host.com" }, 
            "http": { "timeout": 30 }
        }
        """
        dify_config = config.get("dify", {})
        
        self._connector_cache = {
            # 实例化时只传 base_url (静态), api_key 留空
            "dify": DifyConnector(
                base_url=dify_config.get("base_url"),
                # 如果 config 里真的配了 api_key (比如测试环境)，也传进去作为默认值
                api_key=dify_config.get("api_key") 
            ),
            # ...
        }
    
    def shutdown(self) -> None:
        """
        关闭连接器管理器
        """
        # 可以在这里添加关闭逻辑，例如释放资源
        pass
    
    def get_capability_type(self) -> str:
        """
        返回能力类型
        
        Returns:
            str: 能力类型
        """
        return "universal_execution"
    
    def execute(self, connector_name: str, inputs: Dict[str, Any] = None, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        执行连接器操作
        
        Args:
            connector_name: 连接器名称
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
            # 根据连接器名称选择对应的连接器实例
            connector_key = connector_name.lower()
            if connector_key in self._connector_cache:
                connector = self._connector_cache[connector_key]
            elif connector_key.startswith("http_"):
                # 所有http_开头的连接器都使用HttpConnector
                connector = self._connector_cache["http"]
            else:
                raise Exception(f"Unsupported connector: {connector_name}")
            
            # 执行连接器操作
            # params 里此时应该包含 {"dify_api_key": "sk-dynamic-key-from-user"}
            result = connector.execute(inputs, params)
            
            # === 修改点：检查下层返回的状态 ===
            # 如果下层说缺数据，直接透传这个状态，不要包成 SUCCESS
            if result.get("status") == "NEED_INPUT":
                return result 
            
            # 只有真正拿到结果了，才标记为 SUCCESS
            return {
                "status": "SUCCESS",
                "result": result,
                "connector_name": connector_name
            }
        except Exception as e:
            raise Exception(f"Connector execution failed: {str(e)}")
    
    def health_check(self, connector_name: str, params: Dict[str, Any]) -> bool:
        """
        执行健康检查
        
        Args:
            connector_name: 连接器名称
            params: 配置参数
            
        Returns:
            健康检查结果
        """
        connector_key = connector_name.lower()
        if connector_key in self._connector_cache:
            connector = self._connector_cache[connector_key]
        elif connector_key.startswith("http_"):
            connector = self._connector_cache["http"]
        else:
            return False
        
        return connector.health_check(params)
    
    def authenticate(self, connector_name: str, params: Dict[str, Any]) -> bool:
        """
        执行鉴权操作
        
        Args:
            connector_name: 连接器名称
            params: 配置参数
            
        Returns:
            鉴权是否成功
        """
        connector_key = connector_name.lower()
        if connector_key in self._connector_cache:
            connector = self._connector_cache[connector_key]
        elif connector_key.startswith("http_"):
            connector = self._connector_cache["http"]
        else:
            return False
        
        return connector.authenticate(params)
