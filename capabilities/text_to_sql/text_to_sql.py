"""文本到SQL转换接口"""
from abc import abstractmethod
from typing import Optional, List, Dict, Any
from ..capability_base import CapabilityBase

class ITextToSQL(CapabilityBase):
    """文本到SQL转换接口定义"""
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化文本到SQL转换能力
        
        config 应包含：
        - agent_id: str
        - agent_meta: dict (可选)
        - 其他配置项如模型路径、数据库连接等
        """
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """
        关闭文本到SQL转换能力
        """
        pass


    def get_capability_type(self) -> str:
        """
        返回能力类型
        """
        return "text_to_sql"

    @abstractmethod
    def execute_query(self, user_query: str, context: dict = None) -> dict:
        """
        执行查询的核心流程：Context -> SQL -> Result
        """
        pass



    

    @abstractmethod
    def execute_query(self, user_query: str, context: dict = None) -> dict:
        """
        执行查询的核心流程：Context -> SQL -> Result
        """
        pass