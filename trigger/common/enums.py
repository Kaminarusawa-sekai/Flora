from enum import Enum


class TaskInstanceStatus(Enum):
    """任务实例状态枚举"""
    PENDING = "PENDING"    # 等待执行
    RUNNING = "RUNNING"    # 正在执行
    SUCCESS = "SUCCESS"    # 执行成功
    FAILED = "FAILED"      # 执行失败


class ScheduleType(Enum):
    """调度类型枚举"""
    ONCE = "ONCE"          # 单次执行
    CRON = "CRON"          # 定时执行
    LOOP = "LOOP"          # 循环执行
