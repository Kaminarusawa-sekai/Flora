from enum import Enum


class SignalStatus(Enum):
    """
    信号状态枚举
    """
    NORMAL = "NORMAL"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"
