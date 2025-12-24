from abc import ABC, abstractmethod
from typing import List, Optional
from common.dialog import DialogTurn
from ..base import BaseManager

class IContextManagerCapability(BaseManager):
    """
    上下文管理服务接口，用于管理对话历史和上下文
    """
    def __init__(self):
        super().__init__()

    @abstractmethod
    def add_turn(self, turn: DialogTurn) -> int:
        """
        添加一个对话轮次到上下文
        
        Args:
            turn: 对话轮次对象
            
        Returns:
            轮次ID
        """
        pass
    
    @abstractmethod
    def get_turn(self, turn_id: int) -> Optional[DialogTurn]:
        """
        根据ID获取对话轮次
        
        Args:
            turn_id: 轮次ID
            
        Returns:
            对话轮次对象，不存在则返回None
        """
        pass
    
    @abstractmethod
    def get_recent_turns(self, limit: int = 10) -> List[DialogTurn]:
        """
        获取最近的对话轮次
        
        Args:
            limit: 返回的最大轮次数
            
        Returns:
            对话轮次列表，按时间戳倒序排列
        """
        pass
    
    @abstractmethod
    def get_all_turns(self) -> List[DialogTurn]:
        """
        获取所有对话轮次
        
        Returns:
            对话轮次列表，按时间戳正序排列
        """
        pass
    
    @abstractmethod
    def update_turn(self, turn_id: int, enhanced_utterance: str) -> bool:
        """
        更新对话轮次的增强型对话
        
        Args:
            turn_id: 轮次ID
            enhanced_utterance: 增强型对话内容
            
        Returns:
            更新是否成功
        """
        pass
    
    @abstractmethod
    def compress_context(self, n: int) -> bool:
        """
        压缩上下文，将最近的n轮对话合并或精简
        
        Args:
            n: 要压缩的轮次数
            
        Returns:
            压缩是否成功
        """
        pass
    
    @abstractmethod
    def clear_context(self, n: int = 10) -> bool:
        """
        清空n轮前的上下文，保留最近的n轮对话
        
        Args:
            n: 要保留的最近轮次数，默认10
            
        Returns:
            清空是否成功
        """
        pass
    
    @abstractmethod
    def get_context_length(self) -> int:
        """
        获取当前上下文的长度
        
        Returns:
            对话轮次数量
        """
        pass
    
    @abstractmethod
    def get_turns_by_session(self, session_id: str, limit: int = 20, offset: int = 0) -> List[DialogTurn]:
        """
        根据会话ID获取对话轮次
        
        Args:
            session_id: 会话ID
            limit: 返回的最大轮次数
            offset: 偏移量
            
        Returns:
            对话轮次列表，按时间戳倒序排列
        """
        pass
    
    @abstractmethod
    def get_turns_by_user(self, user_id: str, limit: int = 20, offset: int = 0) -> List[DialogTurn]:
        """
        根据用户ID获取对话轮次
        
        Args:
            user_id: 用户ID
            limit: 返回的最大轮次数
            offset: 偏移量
            
        Returns:
            对话轮次列表，按时间戳倒序排列
        """
        pass
    
    @abstractmethod
    def update_turn_user_id(self, session_id: str, old_user_id: str, new_user_id: str) -> bool:
        """
        更新会话中所有轮次的用户ID（用于匿名转正式）
        
        Args:
            session_id: 会话ID
            old_user_id: 旧用户ID
            new_user_id: 新用户ID
            
        Returns:
            更新是否成功
        """
        pass
