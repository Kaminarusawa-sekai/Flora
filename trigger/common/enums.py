from enum import Enum


class ScheduleType(str, Enum):
    """调度类型枚举"""
    IMMEDIATE = "IMMEDIATE"  # 即时任务
    CRON = "CRON"          # 定时任务
    DELAYED = "DELAYED"    # 延迟任务
    LOOP = "LOOP"          # 循环任务
    INTERVAL_LOOP = "INTERVAL_LOOP"  # 带间隔的循环任务


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"        # 等待调度
    SCHEDULED = "SCHEDULED"    # 已调度
    DISPATCHED = "DISPATCHED"  # 已分发到外部系统
    RUNNING = "RUNNING"        # 执行中
    SUCCESS = "SUCCESS"        # 成功
    FAILED = "FAILED"          # 失败
    CANCELLED = "CANCELLED"    # 已取消
