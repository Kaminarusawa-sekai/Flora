# 临时文件，用于检查函数签名和调用的一致性
from typing import Dict, Any, Optional
from datetime import datetime

# 模拟函数定义
def push_status_to_external(
    task_id: str,
    status: str,
    trace_id: Optional[str] = None,
    node_id: Optional[str] = None,
    scheduled_time: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """模拟函数"""
    print(f"task_id: {task_id}")
    print(f"status: {status}")
    print(f"trace_id: {trace_id}")
    print(f"node_id: {node_id}")
    print(f"scheduled_time: {scheduled_time}")
    print(f"metadata: {metadata}")
    return True

# 模拟函数调用
task_id = "test_task_id"
trace_id = "test_trace_id"
scheduled_time = datetime.now()
metadata = {
    "definition_id": "test_def_id",
    "trace_id": "test_trace_id",
    "input_params": {"test": "param"},
    "schedule_config": {"type": "cron"},
    "round_index": 0
}

# 当前调用方式（已修正）
success = push_status_to_external(
    task_id=task_id,
    status="READY_FOR_EXEC