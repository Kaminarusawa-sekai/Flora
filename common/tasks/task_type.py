from enum import Enum

class TaskType(str, Enum):
    ONE_TIME = "one_time"
    LOOP = "loop"