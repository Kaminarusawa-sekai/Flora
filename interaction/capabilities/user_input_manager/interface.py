from typing import Dict, Any
from abc import abstractmethod
from ..base import BaseManager
from ...common import UserInputDTO

class IUserInputManagerCapability(BaseManager):
    """用户输入管理器接口"""
    
    @abstractmethod
    def process_input(self, user_input: UserInputDTO) -> Dict[str, Any]:
        """处理用户输入
        
        Args:
            user_input: 用户输入DTO
            
        Returns:
            处理后的输入数据，包含会话信息
        """
        pass