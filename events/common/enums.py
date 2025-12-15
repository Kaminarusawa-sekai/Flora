from enum import Enum


class ActorType(str, Enum):
    AGENT = "AGENT"
    GROUP_AGG = "GROUP_AGG"
    SINGLE_AGG = "SINGLE_AGG"
    EXECUTION = "EXECUTION"


class ScheduleType(str, Enum):
    ONCE = "ONCE"
    CRON = "CRON"
    LOOP = "LOOP"


class TaskInstanceStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"