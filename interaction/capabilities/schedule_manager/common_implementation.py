from typing import Dict, Any, Optional
from .interface import IScheduleManager
from ...common import (
    ScheduleDTO,
    TaskDraftDTO
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonScheduleManager(IScheduleManager):
    """调度管理器 - 处理任务的调度"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化调度管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
    
    def shutdown(self) -> None:
        """关闭调度管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "schedule"
    
    def parse_schedule_expression(self, natural_language: str, user_timezone: str = "Asia/Shanghai") -> Optional[ScheduleDTO]:
        """解析自然语言调度表达式
        
        Args:
            natural_language: 用户原始说法，如 "每天早上8点"
            user_timezone: 用户时区
            
        Returns:
            调度信息DTO，解析失败返回None
        """
        # 简化的自然语言解析，实际应该调用NLP服务或专门的时间表达式解析库
        schedule_type = "ONCE"
        cron_expression = None
        next_trigger_time = None
        
        # 解析调度类型
        if any(keyword in natural_language for keyword in ["每天", "每周", "每月", "每小时", "每隔"]):
            schedule_type = "RECURRING"
        
        # 示例：解析"每天早上8点" -> cron "0 8 * * *"
        if "每天早上8点" in natural_language:
            cron_expression = "0 8 * * *"
        elif "每周一" in natural_language:
            cron_expression = "0 0 * * 1"
        elif "每小时" in natural_language:
            cron_expression = "0 * * * *"
        
        return ScheduleDTO(
            type=schedule_type,
            cron_expression=cron_expression,
            natural_language=natural_language,
            next_trigger_time=next_trigger_time,
            timezone=user_timezone,
            max_runs=None,
            end_time=None
        )
    
    def validate_cron_expression(self, cron_expression: str) -> bool:
        """验证cron表达式是否合法
        
        Args:
            cron_expression: 标准cron表达式
            
        Returns:
            是否合法
        """
        # 简化的cron验证，实际应该使用专门的cron解析库
        if not cron_expression:
            return False
        
        parts = cron_expression.split()
        if len(parts) != 5:
            return False
        
        # 这里可以添加更详细的cron验证逻辑
        
        return True
    
    def register_scheduled_task(self, task_id: str, schedule: ScheduleDTO) -> bool:
        """向调度引擎注册定时任务
        
        Args:
            task_id: 任务ID
            schedule: 调度信息DTO
            
        Returns:
            是否注册成功
        """
        # 这里应该调用实际的调度引擎API，如Quartz、Celery或Airflow
        # 简化实现，返回True表示成功
        return True
    
    def unregister_scheduled_task(self, task_id: str) -> bool:
        """取消注册定时任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        # 这里应该调用实际的调度引擎API取消任务
        # 简化实现，返回True表示成功
        return True
    
    def update_scheduled_task(self, task_id: str, new_schedule: ScheduleDTO) -> bool:
        """更新已注册的定时任务
        
        Args:
            task_id: 任务ID
            new_schedule: 新的调度信息DTO
            
        Returns:
            是否更新成功
        """
        # 先取消注册，再重新注册
        if self.unregister_scheduled_task(task_id):
            return self.register_scheduled_task(task_id, new_schedule)
        return False
    
    def calculate_next_trigger_time(self, schedule: ScheduleDTO) -> Optional[float]:
        """计算下次触发时间
        
        Args:
            schedule: 调度信息DTO
            
        Returns:
            下次触发时间戳，计算失败返回None
        """
        # 这里应该使用cron表达式或自然语言时间计算下次触发时间
        # 简化实现，返回None表示需要进一步计算
        return schedule.next_trigger_time