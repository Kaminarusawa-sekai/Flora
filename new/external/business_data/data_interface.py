"""业务数据抽象接口"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional


class BusinessDataInterface(ABC):
    """
    业务数据访问的抽象接口，定义数据查询和操作的标准方法
    """
    
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        执行业务数据查询
        
        Args:
            query: 查询语句
            params: 查询参数（可选）
            
        Returns:
            查询结果列表，每条记录为字典形式
        """
        pass
    
    @abstractmethod
    def close(self) -> None:
        """
        关闭连接，释放资源
        """
        pass
    
    @abstractmethod
    def begin_transaction(self) -> Any:
        """
        开始事务
        
        Returns:
            事务对象
        """
        pass
    
    @abstractmethod
    def commit_transaction(self, transaction: Any) -> None:
        """
        提交事务
        
        Args:
            transaction: 事务对象
        """
        pass
    
    @abstractmethod
    def rollback_transaction(self, transaction: Any) -> None:
        """
        回滚事务
        
        Args:
            transaction: 事务对象
        """
        pass
