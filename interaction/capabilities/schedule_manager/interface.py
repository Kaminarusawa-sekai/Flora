from typing import Dict, Any, Optional
from abc import abstractmethod
from ..base import BaseManager
from common import (
    ScheduleDTO
)

class IScheduleManagerCapability(BaseManager):
    """定时/循环任务调度管理器接口"""
    
    @abstractmethod
    def parse_schedule_expression(self, natural_language: str, user_timezone: str = "Asia/Shanghai") -> Optional[ScheduleDTO]:
        """解析自然语言调度表达式
        
        Args:
            natural_language: 用户原始说法，如 "每天早上8点"
            user_timezone: 用户时区
            
        Returns:
            调度信息DTO，解析失败返回None
        """
        pass
    
    @abstractmethod
    def validate_cron_expression(self, cron_expression: str) -> bool:
        """验证cron表达式是否合法
        
        Args:
            cron_expression: 标准cron表达式
            
        Returns:
            是否合法
        """
        pass
    
    @abstractmethod
    def register_scheduled_task(self, task_id: str, schedule: ScheduleDTO) -> bool:
        """向调度引擎注册定时任务
        
        Args:
            task_id: 任务ID
            schedule: 调度信息DTO
            
        Returns:
            是否注册成功
        """
        pass
    
    @abstractmethod
    def unregister_scheduled_task(self, task_id: str) -> bool:
        """取消注册定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        pass
    
    @abstractmethod
    def update_scheduled_task(self, task_id: str, new_schedule: ScheduleDTO) -> bool:
        """更新已注册的定时任务
        
        Args:
            task_id: 任务ID
            new_schedule: 新的调度信息DTO
            
        Returns:
            是否更新成功
        """
        pass
    
    @abstractmethod
    def calculate_next_trigger_time(self, schedule: ScheduleDTO) -> Optional[float]:
        """计算下次触发时间
        
        Args:
            schedule: 调度信息DTO
            
        Returns:
            下次触发时间戳，计算失败返回None
        """
        pass