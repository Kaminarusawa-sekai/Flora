import logging
from fastapi import APIRouter, Depends, HTTPException, status, Path, Body
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# 导入依赖注入
from ..deps import get_lifecycle_service, get_signal_service, get_db_session 
from services.lifecycle_service import LifecycleService
from services.signal_service import SignalService
from common.signal import SignalStatus

# 导入 Pydantic 模型
from ...schemas.request import (
    StartTraceRequest, 
    SplitTaskRequest, 
    ControlNodeRequest,
    ExecutionEventRequest  # 新增：执行事件请求模型
)


router = APIRouter(prefix="/traces", tags=["Trace Management"])


@router.post("/start", status_code=status.HTTP_201_CREATED)
async def start_trace(
    request: StartTraceRequest,
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    启动一个新的 Trace。
    需要外部生成 trace_id 和 request_id 传入。
    """
    try:
        trace_id = await lifecycle_svc.start_trace(
            session=session,
            input_params=request.input_params,
            request_id=request.request_id,  # 传入 request_id
            trace_id=request.trace_id,      # 传入 trace_id

            user_id=request.user_id
        )
        return {"trace_id": trace_id, "status": "created"}
    except Exception as e:
        # 捕获可能的数据库唯一键冲突等
        logger.error(f"Failed to start trace: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Failed to start trace: {str(e)}")


# ------------------------------------------------------------------
# 新增：通用事件接收 (对应执行系统的 Args)
# ------------------------------------------------------------------
@router.post("/events", status_code=status.HTTP_200_OK)
async def report_execution_event(
    request: ExecutionEventRequest,
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service),
    session: AsyncSession = Depends(get_db_session),
    signal_svc: SignalService = Depends(get_signal_service), # 引入信号服务用于返回指令
):
    """
    Worker 汇报接口。
    Response 会携带控制指令 (Piggyback Control)，减少 Worker 的轮询请求。
    """
    try:
        # 1. 处理数据上报 (Write)
        # model_dump() 会将 Pydantic 对象转为纯 Dict，完美适配 Service 签名
        await lifecycle_svc.sync_execution_state(
            session=session,
            execution_args=request.model_dump()
        )
        
        # 2. 检查是否有控制信号 (Read) - 顺便捎带回去
        # 优先查 Trace 级信号，再查 Node 级信号 (如果你的业务支持单节点控制)
        command = "CONTINUE"
        
        # 假设 signal_svc 有个快速查缓存的方法 check_signal
        # 如果 trace 被暂停或取消，这里立刻返回
        signal = await signal_svc.check_signal(request.trace_id, session=session)
        if signal:
            command = signal # 例如 "CANCEL" 或 "PAUSE"

        return {
            "received": True,
            "command": command  # Worker 收到这个字段后决定是否抛出异常停止运行
        }
        
    except Exception as e:
        # 这里记录 Error Log
        logger.error(f"Event sync failed: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Event sync failed: {str(e)}")


@router.post("/{trace_id}/control/trace")
async def control_whole_trace(
    trace_id: str,
    request: ControlNodeRequest,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    控制整个链路 (Cancel/Pause/Resume Trace)
    """
    try:
        # 将枚举值转换为 SignalStatus
        from common.signal import SignalStatus
        signal_map = {
            "CANCEL": SignalStatus.CANCELLED,
            "PAUSE": SignalStatus.PAUSED,
            "RESUME": SignalStatus.NORMAL
        }
        
        await signal_svc.send_signal(
            session,
            trace_id=trace_id,
            signal=signal_map[request.signal.value] # 取 Enum 的值 (String)
        )
        return {"status": "success", "signal": request.signal}
    except Exception as e:
        logger.error(f"Failed to control trace {trace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


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
        current_signal = await signal_svc.check_signal(trace_id, session=session)
        return {
            "trace_id": trace_id,
            "global_signal": current_signal or "NORMAL"
        }
    except ValueError as e:
        logger.error(f"Failed to get trace signal for {trace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/latest-by-request/{request_id}")
async def get_latest_trace(
    request_id: str,
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    根据业务 request_id 查找最新的 trace_id
    """
    trace_id = await lifecycle_svc.get_latest_trace_by_request(session, request_id)
    if not trace_id:
        raise HTTPException(status_code=404, detail="Trace not found for this request_id")
    
    return {"request_id": request_id, "trace_id": trace_id}


@router.post("/{trace_id}/split", status_code=status.HTTP_200_OK)
async def split_task(
    request: SplitTaskRequest,
    trace_id: str = Path(..., description="链路ID"),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Agent 决策后调用此接口，在当前 Parent 节点下挂载子任务。
    """
    try:
        # 转换 subtasks 数据结构
        subtasks_data = [t.model_dump() for t in request.subtasks_meta]
        
        # 调用 Service
        child_ids = await lifecycle_svc.expand_topology(
            session=session,
            parent_id=request.parent_id,
            subtasks_meta=subtasks_data,
            trace_id=trace_id,  # 传入 trace_id 用于校验 parent_id 是否属于该 trace
            context_snapshot=request.reasoning_snapshot # 传入决策快照
        )
        
        return {
            "trace_id": trace_id,
            "parent_id": request.parent_id,
            "new_child_ids": child_ids,
            "count": len(child_ids)
        }
    except ValueError as e:
        # 捕获 Service 层抛出的逻辑校验错误 (如 Parent not found, Trace mismatch)
        logger.error(f"Failed to split task for trace {trace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Internal error when splitting task for trace {trace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{trace_id}/control/nodes/{instance_id}")
async def control_specific_node(
    trace_id: str,
    instance_id: str,
    request: ControlNodeRequest,
    signal_svc: SignalService = Depends(get_signal_service),
    session: AsyncSession = Depends(get_db_session),
):
    """
    控制特定节点及其子树 (Cascade Control)
    """
    try:
        # 将请求中的字符串信号转换为枚举值
        from common.signal import SignalStatus
        signal_map = {
            "CANCEL": SignalStatus.CANCELLED,
            "PAUSE": SignalStatus.PAUSED,
            "RESUME": SignalStatus.NORMAL
        }
        signal = signal_map[request.signal.value]
        
        # 同时传入 trace_id 和 instance_id 确保安全
        await signal_svc.send_signal(
            session,
            trace_id=trace_id,
            instance_id=instance_id, # 指定节点
            signal=signal
        )
        return {
            "status": "success",
            "signal": request.signal,
            "scope": "subtree"
        }
    except Exception as e:
        logger.error(f"Failed to control node {instance_id} in trace {trace_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=400, detail=str(e))