"""任务事件定义"""
from enum import Enum
from typing import Dict, Any, Optional, List
from datetime import datetime


class TaskEventType(Enum):
    """任务事件类型枚举"""
    TASK_CREATED = "task_created"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_PROGRESS = "task_progress"
    TASK_RESUMED = "task_resumed"
    TASK_PAUSED = "task_paused"
    TASK_QUEUED = "task_queued"


class TaskEvent:
    """
    任务事件类，基于原Observer/task_event.py迁移和扩展
    用于记录任务执行过程中的各种状态变化
    """
    
    def __init__(self,
                 task_id: str,
                 event_type: TaskEventType,
                 source: str,
                 data: Optional[Dict[str, Any]] = None,
                 error: Optional[str] = None,
                 progress: Optional[float] = None,
                 timestamp: Optional[datetime] = None):
        """
        初始化任务事件
        
        Args:
            task_id: 任务ID
            event_type: 事件类型
            source: 事件源
            data: 事件数据
            error: 错误信息（如果有）
            progress: 任务进度（0-1）
            timestamp: 事件时间戳
        """
        self.task_id = task_id
        self.event_type = event_type
        self.source = source
        self.data = data or {}
        self.error = error
        self.progress = progress
        self.timestamp = timestamp or datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        
        Returns:
            事件的字典表示
        """
        return {
            "task_id": self.task_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "error": self.error,
            "progress": self.progress,
            "timestamp": self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskEvent':
        """
        从字典创建TaskEvent对象
        
        Args:
            data: 事件数据字典
            
        Returns:
            TaskEvent对象
        """
        timestamp = data.get('timestamp')
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        
        return cls(
            task_id=data['task_id'],
            event_type=TaskEventType(data['event_type']),
            source=data['source'],
            data=data.get('data', {}),
            error=data.get('error'),
            progress=data.get('progress'),
            timestamp=timestamp
        )
    
    def is_success_event(self) -> bool:
        """
        判断是否为成功相关事件
        
        Returns:
            是否为成功事件
        """
        return self.event_type in [
            TaskEventType.TASK_CREATED,
            TaskEventType.TASK_STARTED,
            TaskEventType.TASK_COMPLETED,
            TaskEventType.TASK_PROGRESS,
            TaskEventType.TASK_RESUMED,
            TaskEventType.TASK_QUEUED
        ]
    
    def is_failure_event(self) -> bool:
        """
        判断是否为失败相关事件
        
        Returns:
            是否为失败事件
        """
        return self.event_type in [
            TaskEventType.TASK_FAILED,
            TaskEventType.TASK_CANCELLED
        ]
    
    def __str__(self) -> str:
        """
        字符串表示
        
        Returns:
            事件的字符串表示
        """
        return f"TaskEvent(task_id={self.task_id}, type={self.event_type.value}, source={self.source})"


class TaskEventBatch:
    """
    任务事件批次，用于批量处理事件
    """
    
    def __init__(self):
        """初始化事件批次"""
        self.events: List[TaskEvent] = []
    
    def add_event(self, event: TaskEvent) -> None:
        """
        添加事件到批次
        
        Args:
            event: 任务事件
        """
        self.events.append(event)
    
    def get_events_by_type(self, event_type: TaskEventType) -> List[TaskEvent]:
        """
        根据事件类型获取事件
        
        Args:
            event_type: 事件类型
            
        Returns:
            事件列表
        """
        return [e for e in self.events if e.event_type == event_type]
    
    def get_events_by_task(self, task_id: str) -> List[TaskEvent]:
        """
        根据任务ID获取事件
        
        Args:
            task_id: 任务ID
            
        Returns:
            事件列表
        """
        return [e for e in self.events if e.task_id == task_id]
    
    def to_dict_list(self) -> List[Dict[str, Any]]:
        """
        转换为字典列表
        
        Returns:
            事件字典列表
        """
        return [event.to_dict() for event in self.events]
    
    @property
    def size(self) -> int:
        """
        获取批次大小
        
        Returns:
            事件数量
        """
        return len(self.events)
