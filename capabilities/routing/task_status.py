"""任务状态定义"""
from enum import Enum


class TaskStatus(Enum):
    """任务状态枚举"""
    CREATED = "created"  # 任务已创建
    PROCESSING = "processing"  # 任务处理中
    COMPLETED = "completed"  # 任务已完成
    FAILED = "failed"  # 任务失败
    CANCELLED = "cancelled"  # 任务已取消
    PENDING = "pending"  # 任务待处理
    PAUSED = "paused"  # 任务已暂停
    QUEUED = "queued"  # 任务已排队
    RESUMED = "resumed"  # 任务已恢复


class TaskDependency:
    """任务依赖关系"""
    def __init__(self, task_id: str, dependency_type: str = "execution"):
        self.task_id = task_id
        self.dependency_type = dependency_type  # execution, data, etc.


class TaskResult:
    """任务结果"""
    def __init__(self, task_id: str, result_data: dict, status: TaskStatus = TaskStatus.COMPLETED):
        self.task_id = task_id
        self.result_data = result_data
        self.status = status
        self.timestamp = None  # 可以添加时间戳字段


class TaskError:
    """任务错误"""
    def __init__(self, task_id: str, error_message: str, error_type: str = "execution"):
        self.task_id = task_id
        self.error_message = error_message
        self.error_type = error_type
