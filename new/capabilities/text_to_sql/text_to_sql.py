"""文本到SQL转换接口"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class TextToSQL(ABC):
    """文本到SQL转换接口定义"""
    
    @abstractmethod
    async def generate_sql(self, natural_language_query: str, **kwargs) -> str:
        """
        从自然语言查询生成SQL
        
        Args:
            natural_language_query: 自然语言查询语句
            **kwargs: 其他参数
            
        Returns:
            生成的SQL语句
        """
        pass
    
    @abstractmethod
    async def execute_sql(self, sql: str, **kwargs) -> Dict[str, Any]:
        """
        执行SQL查询
        
        Args:
            sql: 要执行的SQL语句
            **kwargs: 其他参数
            
        Returns:
            查询结果
        """
        pass
    
    @abstractmethod
    async def get_table_info(self, table_name: Optional[str] = None) -> Dict[str, Any]:
        """
        获取表结构信息
        
        Args:
            table_name: 表名，可选。如果不提供，获取所有表的信息
            
        Returns:
            表结构信息
        """
        pass
    
    @abstractmethod
    async def add_training_data(self, query: str, sql: str) -> bool:
        """
        添加训练数据
        
        Args:
            query: 自然语言查询
            sql: 对应的SQL语句
            
        Returns:
            是否添加成功
        """
        pass
    
    @abstractmethod
    async def get_training_data(self) -> List[Dict[str, Any]]:
        """
        获取所有训练数据
        
        Returns:
            训练数据列表
        """
        pass