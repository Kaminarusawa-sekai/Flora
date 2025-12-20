from fastapi import APIRouter, Query, HTTPException, Depends
from typing import List, Optional

# 导入依赖注入
from ..deps import get_observer_service, get_db_session
from ....services.observer_service import ObserverService
from ....external.db.base import TaskInstanceRepository
from ....common.task_instance import TaskInstance
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/traces")


@router.get("/{trace_id}/tasks", response_model=List[TaskInstance])
async def list_tasks_in_trace(
    trace_id: str,
    status: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    layer: Optional[int] = Query(None),
    role: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    observer_svc: ObserverService = Depends(get_observer_service)
):
    """
    多维筛选 trace 内的任务节点。
    支持组合过滤：status + layer + actor_type + role
    """
    filters = {}
    if status: 
        filters["status"] = status
    if actor_type: 
        filters["actor_type"] = actor_type
    if layer is not None: 
        filters["layer"] = layer
    if role is not None: 
        filters["role"] = role

    # 使用观察者服务获取任务列表
    trace_instances = await observer_svc.get_trace_instances(trace_id)
    
    # 在内存中进行过滤
    filtered_tasks = []
    for task in trace_instances:
        match = True
        for key, value in filters.items():
            if getattr(task, key, None) != value:
                match = False
                break
        if match:
            filtered_tasks.append(task)
    
    # 分页
    paginated_tasks = filtered_tasks[offset:offset+limit]
    return paginated_tasks


@router.get("/{trace_id}/status")
async def get_trace_status(
    trace_id: str,
    observer_svc: ObserverService = Depends(get_observer_service)
):
    """
    获取指定跟踪ID的状态摘要
    """
    summary = await observer_svc.get_trace_status_summary(trace_id)
    return summary


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    observer_svc: ObserverService = Depends(get_observer_service)
):
    """
    获取指定任务ID的详细信息
    """
    task = await observer_svc.get_task_instance(task_id)
    if task:
        return task
    return {"error": "Task not found"}


@router.get("/ready-tasks")
async def get_ready_tasks(
    observer_svc: ObserverService = Depends(get_observer_service)
):
    """
    获取所有就绪待执行的任务
    """
    ready_tasks = await observer_svc.get_ready_tasks()
    return {
        "count": len(ready_tasks),
        "tasks": [task.model_dump() for task in ready_tasks]
    }