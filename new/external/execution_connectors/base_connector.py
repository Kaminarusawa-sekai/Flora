"""执行连接抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseConnector(ABC):
    """
    执行连接的抽象接口，定义执行操作的标准方法
    """
    
    @abstractmethod
    def execute(self, instruction: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行指令
        
        Args:
            instruction: 执行指令
            params: 执行参数（可选）
            
        Returns:
            执行结果
        """
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """
        初始化连接器
        
        Returns:
            是否初始化成功
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭连接器，释放资源
        """
        pass
    
    @abstractmethod
    def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            连接是否健康
        """
        pass
