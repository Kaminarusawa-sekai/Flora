from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone


class TaskDefinitionRepo(ABC):
    """任务定义仓库接口"""
    
    @abstractmethod
    async def create(self, name: str, content: dict = None, cron_expr: Optional[str] = None, loop_config: dict = None, schedule_type: str = "IMMEDIATE", schedule_config: dict = None, is_active: bool = True, is_temporary: bool = False, created_at: datetime = None) -> any:
        """创建任务定义"""
        pass
    
    @abstractmethod
    async def get(self, def_id: str) -> any:
        """获取单个任务定义"""
        pass

    @abstractmethod
    async def update(self, def_id: str, **kwargs) -> any:
        """
        更新任务定义

        支持的字段：
        - cron_expr: CRON 表达式
        - loop_config: 循环配置
        - schedule_config: 调度配置
        - is_active: 是否激活
        - content: 任务内容（包含 root_agent_id 等）
        """
        pass
    
    @abstractmethod
    async def list_active_cron(self) -> List[any]:
        """获取所有活跃的CRON任务定义"""
        pass
    
    @abstractmethod
    async def update_last_triggered_at(self, def_id: str, last_triggered_at: datetime) -> None:
        """更新任务的最后触发时间"""
        pass
    
    @abstractmethod
    async def deactivate(self, def_id: str) -> None:
        """停用任务"""
        pass
    
    @abstractmethod
    async def activate(self, def_id: str) -> None:
        """激活任务"""
        pass


class TaskInstanceRepo(ABC):
    """任务实例仓库接口"""
    
    @abstractmethod
    async def create(self, definition_id: str, trace_id: str, input_params: dict = None, schedule_type: str = "ONCE", round_index: int = 0, depends_on: list = None) -> any:
        """创建任务实例"""
        pass
    
    @abstractmethod
    async def get(self, instance_id: str) -> any:
        """获取单个任务实例"""
        pass
    
    @abstractmethod
    async def update_status(self, instance_id: str, status: str, error_msg: Optional[str] = None) -> None:
        """更新任务实例状态"""
        pass
    
    @abstractmethod
    async def list_by_trace_id(self, trace_id: str) -> List[any]:
        """获取某个trace下的所有任务实例"""
        pass
    
    @abstractmethod
    async def update_finished_at(self, instance_id: str, finished_at: datetime, status: str, output_ref: Optional[str] = None, error_msg: Optional[str] = None) -> None:
        """更新任务实例的完成时间和结果"""
        pass
    
    @abstractmethod
    async def get_running_instances(self, timeout_seconds: int = 3600) -> List[any]:
        """获取运行超时的任务实例"""
        pass


class ScheduledTaskRepo(ABC):
    """调度任务仓库接口"""
    
    @abstractmethod
    async def create(self, task) -> any:
        """创建调度任务"""
        pass
    
    @abstractmethod
    async def get(self, task_id: str) -> any:
        """获取单个调度任务"""
        pass
    
    @abstractmethod
    async def get_pending_tasks(self, before_time: datetime, limit: int = 100) -> List[any]:
        """获取待处理的调度任务"""
        pass
    
    @abstractmethod
    async def update_status(self, task_id: str, status: str) -> None:
        """更新调度任务状态"""
        pass

    @abstractmethod
    async def update_scheduled_task(self, task_id: str, **kwargs) -> any:
        """
        更新调度任务

        支持的字段：
        - scheduled_time: 调度时间
        - schedule_config: 调度配置
        - input_params: 输入参数
        - priority: 优先级

        只允许修改 PENDING 状态的任务
        """
        pass

    @abstractmethod
    async def reschedule_task(self, task_id: str, new_scheduled_time: datetime, new_schedule_config: dict = None) -> any:
        """
        重新调度任务

        将任务状态重置为 PENDING，并更新调度时间

        Args:
            task_id: 任务ID
            new_scheduled_time: 新的调度时间
            new_schedule_config: 新的调度配置（可选）

        Returns:
            更新后的任务对象，如果任务不存在或状态不允许重新调度则返回 None
        """
        pass

    @abstractmethod
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消调度任务

        Args:
            task_id: 任务ID

        Returns:
            是否取消成功
        """
        pass
    
    @abstractmethod
    async def record_retry(self, task_id: str, error_msg: str) -> None:
        """记录任务重试"""
        pass
