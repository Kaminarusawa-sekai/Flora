from typing import Dict, Any, Optional, List, Type
from abc import ABC, abstractmethod


class BaseConnector(ABC):
    """
    连接器抽象基类，定义连接器的公共接口
    """
    
    def __init__(self):
        """初始化连接器"""
        pass
    
    @abstractmethod
    def execute(self, inputs: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行连接器操作
        
        Args:
            inputs: 输入参数
            params: 配置参数
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        pass
    
    def _check_missing_inputs(self, inputs: Dict[str, Any]) -> List[str]:
        """
        检查缺失的输入参数
        
        Args:
            inputs: 输入参数字典
            
        Returns:
            List[str]: 缺失的输入参数列表
        """
        return None
    
    def _get_required_params(self, params: Dict[str, Any]) -> List[str]:
        """
        获取必需配置参数列表
        
        Returns:
            List[str]: 必需配置参数列表
        """
        return []
    
    def _get_required_inputs(self) -> List[str]:
        """
        获取必需输入参数列表
        
        Returns:
            List[str]: 必需输入参数列表
        """
        return []
    
    def authenticate(self, params: Dict[str, Any]) -> bool:
        """
        执行鉴权操作
        
        Args:
            params: 配置参数
            
        Returns:
            bool: 鉴权是否成功
        """
        return True
    
    def health_check(self, params: Dict[str, Any]) -> bool:
        """
        执行健康检查
        
        Args:
            params: 配置参数
            
        Returns:
            bool: 健康检查是否通过
        """
        return True
