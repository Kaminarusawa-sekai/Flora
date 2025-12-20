from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

# 导入依赖注入
from ..deps import get_lifecycle_service, get_signal_service, get_db_session 
from ....services.lifecycle_service import LifecycleService
from ....services.signal_service import SignalService

# 导入 Pydantic 模型
from ...schemas.request import StartTraceRequest, SplitTaskRequest, ControlNodeRequest


router = APIRouter(prefix="/traces", tags=["Trace Management"])


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_trace(
    request: StartTraceRequest,
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    启动一个新的事件跟踪
    """
    try:
        trace_id = await lifecycle_svc.start_trace(
            session,
            request.root_def_id,
            request.input_params
        )
        return {"trace_id": trace_id}
    except ValueError as e:
        # 捕获 Service 层抛出的业务错误，如 Definition not found
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{trace_id}/cancel")
async def cancel_trace(
    trace_id: str,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    取消整个跟踪链路
    """
    try:
        await signal_svc.send_signal(session, trace_id=trace_id, signal="CANCEL")
        return {"status": "cancelled", "trace_id": trace_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{trace_id}/pause")
async def pause_trace(
    trace_id: str,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    暂停整个跟踪链路
    """
    try:
        await signal_svc.send_signal(session, trace_id=trace_id, signal="PAUSE")
        return {"status": "paused", "trace_id": trace_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{trace_id}/resume")
async def resume_trace(
    trace_id: str,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    恢复整个跟踪链路
    """
    try:
        await signal_svc.send_signal(session, trace_id=trace_id, signal="RESUME")
        return {"status": "resumed", "trace_id": trace_id}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{trace_id}/status")
async def get_trace_signal(
    trace_id: str,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    查询整个跟踪链路的当前信号状态
    """
    try:
        signal = await signal_svc.check_signal(trace_id, session=session)
        return {
            "trace_id": trace_id,
            "signal": signal
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{trace_id}/split")
async def split_task(
    trace_id: str,
    request: SplitTaskRequest,
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    动态拓扑扩展：在指定父节点下裂变子任务
    """
    try:
        # 将 Pydantic model 转为 list[dict] 传给 Service
        # 注意：这里传入了 trace_id 以便 Service 做一致性校验
        subtasks_data = [t.model_dump() for t in request.subtasks_meta]
        
        child_ids = await lifecycle_svc.expand_topology(
            session,
            trace_id=trace_id,  # 传入 URL 中的 trace_id
            parent_id=request.parent_id,
            subtasks_meta=subtasks_data
        )
        
        return {
            "trace_id": trace_id,
            "parent_id": request.parent_id,
            "child_ids": child_ids,
            "status": "split_completed"
        }
    except ValueError as e:
        # 比如 Parent not found 或 trace_id 不匹配
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{trace_id}/nodes/{instance_id}/control")
async def control_node(
    trace_id: str,
    instance_id: str,
    request: ControlNodeRequest,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    级联控制：向指定节点及其子孙发送信号 (CANCEL/PAUSE)
    """
    try:
        # 同时传入 trace_id 和 instance_id 确保安全
        await signal_svc.send_signal(
            session,
            trace_id=trace_id,
            instance_id=instance_id,
            signal=request.signal
        )
        return {
            "trace_id": trace_id,
            "instance_id": instance_id,
            "signal": request.signal,
            "status": "control_sent"
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))