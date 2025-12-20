from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone


class TaskDefinitionRepo(ABC):
    """任务定义仓库接口"""
    
    @abstractmethod
    async def create(self, name: str, cron_expr: Optional[str] = None, loop_config: dict = None, is_active: bool = True) -> any:
        """创建任务定义"""
        pass
    
    @abstractmethod
    async def get(self, def_id: str) -> any:
        """获取单个任务定义"""
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
