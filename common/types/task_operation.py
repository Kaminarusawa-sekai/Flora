"""任务操作类型定义"""
from enum import Enum


class TaskOperationType(Enum):
    """
    任务操作类型枚举

    定义了所有可能的任务操作类型
    """

    # ========== 新任务创建 ==========
    NEW_TASK = "new_task"                           # 创建新的单次任务
    NEW_LOOP_TASK = "new_loop_task"                 # 创建新的循环任务
    NEW_DELAYED_TASK = "new_delayed_task"           # 创建延时任务
    NEW_SCHEDULED_TASK = "new_scheduled_task"       # 创建定时任务

    # ========== 任务执行控制 ==========
    EXECUTE_TASK = "execute_task"                   # 立即执行任务
    TRIGGER_LOOP_TASK = "trigger_loop_task"         # 立即触发循环任务
    PAUSE_TASK = "pause_task"                       # 暂停任务
    RESUME_TASK = "resume_task"                     # 恢复任务
    CANCEL_TASK = "cancel_task"                     # 取消任务
    RETRY_TASK = "retry_task"                       # 重试任务

    # ========== 循环任务管理 ==========
    MODIFY_LOOP_INTERVAL = "modify_loop_interval"   # 修改循环间隔
    PAUSE_LOOP = "pause_loop"                       # 暂停循环
    RESUME_LOOP = "resume_loop"                     # 恢复循环
    CANCEL_LOOP = "cancel_loop"                     # 取消循环任务

    # ========== 任务修改 ==========
    MODIFY_TASK_PARAMS = "modify_task_params"       # 修改任务参数
    MODIFY_TASK_PRIORITY = "modify_task_priority"   # 修改任务优先级
    MODIFY_TASK_DEADLINE = "modify_task_deadline"   # 修改任务截止时间

    # ========== 结果和过程修改 ==========
    REVISE_RESULT = "revise_result"                 # 修改任务结果
    REVISE_PROCESS = "revise_process"               # 修改任务执行过程
    ROLLBACK_RESULT = "rollback_result"             # 回滚任务结果

    # ========== 任务注释和文档 ==========
    COMMENT_ON_TASK = "comment_on_task"             # 对任务添加评论
    ADD_TASK_NOTE = "add_task_note"                 # 添加任务备注
    UPDATE_TASK_DESCRIPTION = "update_task_description"  # 更新任务描述

    # ========== 任务查询 ==========
    QUERY_TASK_STATUS = "query_task_status"         # 查询任务状态
    QUERY_TASK_RESULT = "query_task_result"         # 查询任务结果
    QUERY_TASK_HISTORY = "query_task_history"       # 查询任务历史
    LIST_TASKS = "list_tasks"                       # 列出任务列表

    # ========== 任务依赖管理 ==========
    ADD_TASK_DEPENDENCY = "add_task_dependency"     # 添加任务依赖
    REMOVE_TASK_DEPENDENCY = "remove_task_dependency"  # 移除任务依赖

    # ========== 任务分组和批处理 ==========
    CREATE_TASK_GROUP = "create_task_group"         # 创建任务组
    ADD_TO_TASK_GROUP = "add_to_task_group"         # 添加到任务组
    EXECUTE_TASK_GROUP = "execute_task_group"       # 执行任务组

    # ========== 其他 ==========
    UNKNOWN = "unknown"                             # 未知操作


class TaskOperationCategory(Enum):
    """任务操作分类"""

    CREATION = "creation"           # 创建类
    EXECUTION = "execution"         # 执行控制类
    LOOP_MANAGEMENT = "loop"        # 循环管理类
    MODIFICATION = "modification"   # 修改类
    QUERY = "query"                 # 查询类
    DEPENDENCY = "dependency"       # 依赖管理类
    GROUPING = "grouping"           # 分组类
    UNKNOWN = "unknown"             # 未知类


# 操作类型到分类的映射
OPERATION_CATEGORY_MAP = {
    # 创建类
    TaskOperationType.NEW_TASK: TaskOperationCategory.CREATION,
    TaskOperationType.NEW_LOOP_TASK: TaskOperationCategory.CREATION,
    TaskOperationType.NEW_DELAYED_TASK: TaskOperationCategory.CREATION,
    TaskOperationType.NEW_SCHEDULED_TASK: TaskOperationCategory.CREATION,

    # 执行控制类
    TaskOperationType.EXECUTE_TASK: TaskOperationCategory.EXECUTION,
    TaskOperationType.TRIGGER_LOOP_TASK: TaskOperationCategory.EXECUTION,
    TaskOperationType.PAUSE_TASK: TaskOperationCategory.EXECUTION,
    TaskOperationType.RESUME_TASK: TaskOperationCategory.EXECUTION,
    TaskOperationType.CANCEL_TASK: TaskOperationCategory.EXECUTION,
    TaskOperationType.RETRY_TASK: TaskOperationCategory.EXECUTION,

    # 循环管理类
    TaskOperationType.MODIFY_LOOP_INTERVAL: TaskOperationCategory.LOOP_MANAGEMENT,
    TaskOperationType.PAUSE_LOOP: TaskOperationCategory.LOOP_MANAGEMENT,
    TaskOperationType.RESUME_LOOP: TaskOperationCategory.LOOP_MANAGEMENT,
    TaskOperationType.CANCEL_LOOP: TaskOperationCategory.LOOP_MANAGEMENT,

    # 修改类
    TaskOperationType.MODIFY_TASK_PARAMS: TaskOperationCategory.MODIFICATION,
    TaskOperationType.MODIFY_TASK_PRIORITY: TaskOperationCategory.MODIFICATION,
    TaskOperationType.MODIFY_TASK_DEADLINE: TaskOperationCategory.MODIFICATION,
    TaskOperationType.REVISE_RESULT: TaskOperationCategory.MODIFICATION,
    TaskOperationType.REVISE_PROCESS: TaskOperationCategory.MODIFICATION,
    TaskOperationType.ROLLBACK_RESULT: TaskOperationCategory.MODIFICATION,
    TaskOperationType.COMMENT_ON_TASK: TaskOperationCategory.MODIFICATION,
    TaskOperationType.ADD_TASK_NOTE: TaskOperationCategory.MODIFICATION,
    TaskOperationType.UPDATE_TASK_DESCRIPTION: TaskOperationCategory.MODIFICATION,

    # 查询类
    TaskOperationType.QUERY_TASK_STATUS: TaskOperationCategory.QUERY,
    TaskOperationType.QUERY_TASK_RESULT: TaskOperationCategory.QUERY,
    TaskOperationType.QUERY_TASK_HISTORY: TaskOperationCategory.QUERY,
    TaskOperationType.LIST_TASKS: TaskOperationCategory.QUERY,

    # 依赖管理类
    TaskOperationType.ADD_TASK_DEPENDENCY: TaskOperationCategory.DEPENDENCY,
    TaskOperationType.REMOVE_TASK_DEPENDENCY: TaskOperationCategory.DEPENDENCY,

    # 分组类
    TaskOperationType.CREATE_TASK_GROUP: TaskOperationCategory.GROUPING,
    TaskOperationType.ADD_TO_TASK_GROUP: TaskOperationCategory.GROUPING,
    TaskOperationType.EXECUTE_TASK_GROUP: TaskOperationCategory.GROUPING,
}


def get_operation_category(operation_type: TaskOperationType) -> TaskOperationCategory:
    """
    获取操作类型的分类

    Args:
        operation_type: 任务操作类型

    Returns:
        TaskOperationCategory: 操作分类
    """
    return OPERATION_CATEGORY_MAP.get(operation_type, TaskOperationCategory.UNKNOWN)
