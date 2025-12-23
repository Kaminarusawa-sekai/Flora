from typing import Dict, Any, Optional, List
from abc import abstractmethod
from ..base import BaseManager
from common import (
    SystemResponseDTO,
    SuggestedActionDTO,
    ActionType,
    TaskStatusSummary
)

class ISystemResponseManagerCapability(BaseManager):
    """系统响应管理器接口"""
    
    @abstractmethod
    def generate_response(self, session_id: str, response_text: str, 
                         suggested_actions: List[SuggestedActionDTO] = None, 
                         task_status: Optional[TaskStatusSummary] = None, 
                         requires_input: bool = False, 
                         awaiting_slot: Optional[str] = None, 
                         display_data: Optional[Dict[str, Any]] = None) -> SystemResponseDTO:
        """生成系统响应
        
        Args:
            session_id: 会话ID
            response_text: 响应文本
            suggested_actions: 建议操作列表
            task_status: 任务状态摘要
            requires_input: 是否需要用户输入
            awaiting_slot: 正在等待的槽位
            display_data: 结构化展示数据
            
        Returns:
            系统响应DTO
        """
        pass
    
    @abstractmethod
    def generate_task_creation_response(self, session_id: str, task_id: str, task_title: str) -> SystemResponseDTO:
        """生成任务创建成功的响应
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            task_title: 任务标题
            
        Returns:
            系统响应DTO
        """
        pass
    
    @abstractmethod
    def generate_task_status_response(self, session_id: str, task_status_info: Dict[str, Any]) -> SystemResponseDTO:
        """生成任务状态响应
        
        Args:
            session_id: 会话ID
            task_status_info: 任务状态信息
            
        Returns:
            系统响应DTO
        """
        pass
    
    @abstractmethod
    def generate_fill_slot_response(self, session_id: str, missing_slots: List[str], draft_id: str) -> SystemResponseDTO:
        """生成填槽请求响应
        
        Args:
            session_id: 会话ID
            missing_slots: 缺失的槽位列表
            draft_id: 草稿ID
            
        Returns:
            系统响应DTO
        """
        pass
    
    @abstractmethod
    def generate_query_response(self, session_id: str, query_result: Dict[str, Any]) -> SystemResponseDTO:
        """生成查询结果响应
        
        Args:
            session_id: 会话ID
            query_result: 查询结果
            
        Returns:
            系统响应DTO
        """
        pass
    
    @abstractmethod
    def generate_error_response(self, session_id: str, error_message: str) -> SystemResponseDTO:
        """生成错误响应
        
        Args:
            session_id: 会话ID
            error_message: 错误信息
            
        Returns:
            系统响应DTO
        """
        pass
    
    @abstractmethod
    def generate_idle_response(self, session_id: str, idle_message: str) -> SystemResponseDTO:
        """生成闲聊模式响应
        
        Args:
            session_id: 会话ID
            idle_message: 闲聊消息
            
        Returns:
            系统响应DTO
        """
        pass