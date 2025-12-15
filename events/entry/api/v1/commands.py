from fastapi import APIRouter, Body, Depends
from typing import Dict, Any

# 导入依赖注入
from ...deps import get_lifecycle_service, get_signal_service
from ...services.lifecycle_service import LifecycleService
from ...services.signal_service import SignalService

router = APIRouter(prefix="/traces")


@router.post("/start")
async def start_trace(
    def_id: str = Body(...),
    params: Dict[str, Any] = Body(default_factory=dict),
    trigger_type: str = Body("MANUAL"),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """
    启动一个新的任务跟踪
    """
    trace_id = await lifecycle_svc.start_new_trace(def_id, params, trigger_type)
    return {"trace_id": trace_id}


@router.post("/{trace_id}/cancel")
async def cancel_trace(
    trace_id: str,
    signal_svc: SignalService = Depends(get_signal_service)
):
    """
    取消指定跟踪ID的所有任务
    """
    await signal_svc.cancel_trace(trace_id)
    return {"status": "cancelled"}


@router.post("/{trace_id}/pause")
async def pause_trace(
    trace_id: str,
    signal_svc: SignalService = Depends(get_signal_service)
):
    """
    暂停指定跟踪ID的所有任务
    """
    await signal_svc.send_signal(trace_id, "PAUSE")
    return {"status": "paused"}


@router.post("/{trace_id}/split")
async def split_task(
    trace_id: str,
    parent_id: str = Body(..., description="父任务ID"),
    split_config: Dict[str, Any] = Body(..., description="拆分配置")
):
    """
    拆分任务，生成子任务
    """
    # 这里应该调用相应的服务来拆分任务
    # 暂时返回一个示例响应
    return {
        "trace_id": trace_id,
        "parent_id": parent_id,
        "split_config": split_config,
        "status": "split_in_progress"
    }


@router.post("/events")
async def handle_event(
    event_type: str = Body(...),
    task_id: str = Body(...),
    output_ref: str = Body(None),
    error_msg: str = Body(None),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """
    处理任务事件，如任务完成
    """
    if event_type == "COMPLETED" and output_ref:
        await lifecycle_svc.handle_task_completed(task_id, output_ref)
    elif event_type == "FAILED" and error_msg:
        await lifecycle_svc.handle_task_failed(task_id, error_msg)
    return {"status": "event_processed"}