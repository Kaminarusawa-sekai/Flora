"""连接器调度器模块"""
from typing import Dict, Any, List, Optional
from .base_connector import BaseConnector
from .registry import connector_registry
from .connector_factory import ConnectorFactory
# 由于common与external是同级目录，使用绝对导入
from common.messages.connector_messages import (
    ExecuteConnectorRequest, PrepareConnectorRequest, CancelConnectorRequest,
    GetConnectorStatusRequest, ConnectorResult, ConnectorError
)


class ConnectorScheduler:
    """
    连接器调度器，实现能力自适应的调度逻辑
    
    核心功能：
    1. 根据连接器能力动态调整调用流程
    2. 支持不同类型的连接器调用（直接执行、准备后执行、取消等）
    3. 提供统一的调用接口，隐藏不同连接器的实现差异
    """
    
    def __init__(self):
        pass
    
    def schedule_request(self, connector_type: str, request_type: str, **kwargs) -> Dict[str, Any]:
        """
        调度连接器请求
        
        Args:
            connector_type: 连接器类型
            request_type: 请求类型
            **kwargs: 请求参数
            
        Returns:
            调度结果
        """
        # 检查连接器是否支持该请求类型
        if not connector_registry.has_capability(connector_type, self._request_type_to_capability(request_type)):
            return ConnectorError(error_code="CAPABILITY_NOT_SUPPORTED", message=f"Connector {connector_type} does not support {request_type}").to_dict()
        
        # 创建连接器实例
        config = kwargs.get("config", {})
        connector = ConnectorFactory.create_connector(connector_type, config)
        
        # 根据请求类型调用相应的方法
        try:
            if request_type == "execute":
                return self._handle_execute_request(connector, **kwargs)
            elif request_type == "prepare":
                return self._handle_prepare_request(connector, **kwargs)
            elif request_type == "cancel":
                return self._handle_cancel_request(connector, **kwargs)
            elif request_type == "get_status":
                return self._handle_get_status_request(connector, **kwargs)
            else:
                return ConnectorError(error_code="UNKNOWN_REQUEST_TYPE", message=f"Unknown request type: {request_type}").to_dict()
        except Exception as e:
            return ConnectorError(error_code="INTERNAL_ERROR", message=str(e)).to_dict()
    
    def schedule_with_prepare(self, connector_type: str, instruction: str, params: Dict[str, Any] = None, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        如果连接器支持准备能力，则先准备后执行
        
        Args:
            connector_type: 连接器类型
            instruction: 执行指令
            params: 执行参数
            config: 连接器配置
            
        Returns:
            执行结果
        """
        # 检查连接器是否支持准备能力
        if connector_registry.has_capability(connector_type, "prepare"):
            # 先准备
            prepare_result = self.schedule_request(connector_type, "prepare", config=config, context={"instruction": instruction, "params": params})
            
            # 如果准备成功，则执行
            if "error" not in prepare_result:
                return self.schedule_request(connector_type, "execute", config=config, instruction=instruction, params=params)
            else:
                return prepare_result
        else:
            # 直接执行
            return self.schedule_request(connector_type, "execute", config=config, instruction=instruction, params=params)
    
    def _handle_execute_request(self, connector: BaseConnector, **kwargs) -> Dict[str, Any]:
        """
        处理执行请求
        
        Args:
            connector: 连接器实例
            **kwargs: 请求参数
            
        Returns:
            执行结果
        """
        instruction = kwargs.get("instruction")
        params = kwargs.get("params", None)
        
        if not instruction:
            return ConnectorError(error_code="MISSING_PARAMETER", message="Missing instruction parameter").to_dict()
        
        result = connector.execute(instruction, params)
        
        if "error" in result or "error_code" in result:
            return result
        else:
            return ConnectorResult(result=result, status="success").to_dict()
    
    def _handle_prepare_request(self, connector: BaseConnector, **kwargs) -> Dict[str, Any]:
        """
        处理准备请求
        
        Args:
            connector: 连接器实例
            **kwargs: 请求参数
            
        Returns:
            准备结果
        """
        context = kwargs.get("context", {})
        result = connector.prepare(context)
        return ConnectorResult(result=result, status="success").to_dict()
    
    def _handle_cancel_request(self, connector: BaseConnector, **kwargs) -> Dict[str, Any]:
        """
        处理取消请求
        
        Args:
            connector: 连接器实例
            **kwargs: 请求参数
            
        Returns:
            取消结果
        """
        task_id = kwargs.get("task_id")
        
        if not task_id:
            return ConnectorError(error_code="MISSING_PARAMETER", message="Missing task_id parameter").to_dict()
        
        result = connector.cancel(task_id)
        return ConnectorResult(result=result, status="success").to_dict()
    
    def _handle_get_status_request(self, connector: BaseConnector, **kwargs) -> Dict[str, Any]:
        """
        处理状态查询请求
        
        Args:
            connector: 连接器实例
            **kwargs: 请求参数
            
        Returns:
            状态查询结果
        """
        task_id = kwargs.get("task_id")
        
        if not task_id:
            return ConnectorError(error_code="MISSING_PARAMETER", message="Missing task_id parameter").to_dict()
        
        result = connector.get_status(task_id)
        return ConnectorResult(result=result, status="success").to_dict()
    
    def _request_type_to_capability(self, request_type: str) -> str:
        """
        将请求类型转换为能力名称
        
        Args:
            request_type: 请求类型
            
        Returns:
            能力名称
        """
        return request_type
