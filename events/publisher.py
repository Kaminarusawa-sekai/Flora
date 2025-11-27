"""
发布者接口定义
为事件发布者提供统一的接口规范
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class Publisher(ABC):
    """发布者抽象类，定义事件发布接口"""
    
    @abstractmethod
    def publish_event(
        self, 
        event_type: str, 
        source: str, 
        data: Optional[Dict[str, Any]] = None, 
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            source: 事件源
            data: 事件数据
            timestamp: 事件时间戳
        """
        pass
    
    @abstractmethod
    def publish_task_event(
        self, 
        task_id: str, 
        event_type: str, 
        source: str, 
        agent_id: str, 
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        发布任务相关事件
        
        Args:
            task_id: 任务ID
            event_type: 事件类型
            source: 事件源
            agent_id: 智能体ID
            data: 事件数据
        """
        pass
