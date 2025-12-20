from fastapi import APIRouter, Body, Depends
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

# 导入依赖注入
from ..deps import get_lifecycle_service, get_signal_service,get_db_session 
from ....services.lifecycle_service import LifecycleService
from ....services.signal_service import SignalService


router = APIRouter(prefix="/traces")


@router.post("/start")
async def start_trace(
    root_def_id: str = Body(...),
    input_params: Dict[str, Any] = Body(default_factory=dict),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    启动一个新的任务跟踪
    """
    trace_id = await lifecycle_svc.start_trace(session, root_def_id, input_params)
    return {"trace_id": trace_id}


@router.post("/{trace_id}/cancel")
async def cancel_trace(
    trace_id: str,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    取消指定跟踪ID的所有任务
    """
    await signal_svc.send_signal(session, trace_id=trace_id, signal="CANCEL")
    return {"status": "cancelled"}


@router.post("/{trace_id}/pause")
async def pause_trace(
    trace_id: str,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    暂停指定跟踪ID的所有任务
    """
    await signal_svc.send_signal(session, trace_id=trace_id, signal="PAUSE")
    return {"status": "paused"}


@router.post("/{trace_id}/split")
async def split_task(
    trace_id: str,
    parent_id: str = Body(..., description="父任务ID"),
    subtasks_meta: List[Dict[str, Any]] = Body(..., description="子任务元数据列表"),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    拆分任务，生成子任务
    subtasks_meta 示例: [
        {"def_id": "AGG_GROUP", "name": "Group A", "params": {...}},
        {"def_id": "AGG_GROUP", "name": "Group B", "params": {...}}
    ]
    """
    child_ids = await lifecycle_svc.expand_topology(session, parent_id, subtasks_meta)
    return {
        "trace_id": trace_id,
        "parent_id": parent_id,
        "child_ids": child_ids,
        "status": "split_completed"
    }


@router.post("/{trace_id}/control/{instance_id}")
async def control_node(
    trace_id: str,
    instance_id: str,
    signal: str = Body(..., description="控制信号，如 CANCEL 或 PAUSE"),
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    级联控制：向指定节点及其所有子孙发送控制信号
    """
    await signal_svc.send_signal(session, instance_id=instance_id, signal=signal)
    return {
        "trace_id": trace_id,
        "instance_id": instance_id,
        "signal": signal,
        "status": "control_sent"
    }