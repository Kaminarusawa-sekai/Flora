from enum import Enum

class MessageType(str, Enum):
    
    # === Task 相关 ===
    TASK_CREATED = "task_created"
    USER_REQUEST = "user_request"
    INIT_CONFIG = "init_config"
    TASK_PAUSED = "task_paused"
    TASK_RESULT = "task_result"

    MCP = "MCP"
    SUBTASK_SPAWNED = "subtask_spawned"
    TASK_GROUP_REQUEST = "task_group_request"
    PARALLEL_TASK_REQUEST = "parallel_task_request"
    RESULT_AGGREGATOR_REQUEST = "result_aggregator_request"
    EXECUTE_TASK = "execute_task"

    AGENT_TASK = "agent_task"

    TASK_STARTED = "task_started"
    TASK_PROGRESS = "task_progress"
    TASK_CANCELLED = "task_cancelled"

    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    EXECUTION_RESULT = "execution_result"

    TASK_GROUP_RESULT = "task_group_result"
