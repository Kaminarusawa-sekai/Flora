"""连接器管理器抽象基类定义"""
from abc import ABC, abstractmethod
from typing import Dict, Any
from ..capability_base import CapabilityBase


class BaseExecution(CapabilityBase):
    """
    执行管理器抽象基类，定义执行管理器的核心接口
    继承自CapabilityBase，负责执行管理器的生命周期和基础元数据
    """
    
    def get_capability_type(self):
        """
        返回能力类型
        """
        return "execution"


    @abstractmethod
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
        pass
    
    @abstractmethod
    def health_check(self, connector_name: str, params: Dict[str, Any]) -> bool:
        """
        执行健康检查
        
        Args:
            connector_name: 连接器名称
            params: 配置参数
            
        Returns:
            健康检查结果
        """
        pass
    
    @abstractmethod
    def authenticate(self, connector_name: str, params: Dict[str, Any]) -> bool:
        """
        执行鉴权操作
        
        Args:
            connector_name: 连接器名称
            params: 配置参数
            
        Returns:
            鉴权是否成功
        """
        pass
