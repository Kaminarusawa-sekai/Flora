from enum import Enum


class ActorType(str, Enum):
    AGENT = "AGENT"
    GROUP_AGG = "GROUP_AGG"
    SINGLE_AGG = "SINGLE_AGG"
    EXECUTION = "EXECUTION"


class NodeType(str, Enum):
    AGENT_ACTOR = "AGENT_ACTOR"       # 负责裂变的算子
    AGGREGATOR_GROUP = "AGG_GROUP"    # 组任务聚合器
    AGGREGATOR_SINGLE = "AGG_SINGLE"  # 单任务聚合器
    EXECUTION_ACTOR = "EXEC_ACTOR"    # 叶子节点执行者


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