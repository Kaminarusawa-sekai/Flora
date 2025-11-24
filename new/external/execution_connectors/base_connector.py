"""执行连接抽象接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class BaseConnector(ABC):
    """
    执行连接的抽象接口，定义执行操作的标准方法
    
    核心思想：
    所有连接器都通过"消息"与系统交互，但支持不同的消息类型组合。
    实现能力自适应的统一契约
    
    基础能力：必须实现execute
    可选能力：可以根据连接器特性选择实现
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化连接器
        
        Args:
            config: 连接器配置
        """
        self.config = config or {}
        self.is_initialized = False
    
    @abstractmethod
    def execute(self, instruction: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        执行指令（基础能力 - 必须实现）
        
        Args:
            instruction: 执行指令
            params: 执行参数（可选）
            
        Returns:
            执行结果
        """
        pass
    
    def initialize(self, skip_health_check: bool = False) -> bool:
        """
        初始化连接器（可选能力）
        
        Args:
            skip_health_check: 是否跳过健康检查（用于测试目的）
            
        Returns:
            是否初始化成功
        """
        self.is_initialized = True
        return True
    
    def close(self) -> None:
        """
        关闭连接器，释放资源（可选能力）
        """
        self.is_initialized = False
    
    def health_check(self) -> bool:
        """
        健康检查（可选能力）
        
        Returns:
            连接是否健康
        """
        return True
    
    def prepare(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备阶段（可选能力 - 支持准备阶段的连接器才处理）
        
        Args:
            context: 准备上下文
            
        Returns:
            准备结果
        """
        return {}
    
    def cancel(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务（可选能力 - 支持中断/取消）
        
        Args:
            task_id: 任务ID
            
        Returns:
            取消结果
        """
        return {"message": "Cancel not supported"}
    
    def get_status(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务状态（可选能力 - 支持状态查询）
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态
        """
        return {"status": "unknown"}
