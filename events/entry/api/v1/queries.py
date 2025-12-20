from fastapi import APIRouter, Query, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel

# 导入依赖注入
from ..deps import get_observer_service, get_db_session, get_connection_manager
from ....services.observer_service import ObserverService
from ....services.websocket_manager import ConnectionManager
from ....common.event_instance import EventInstance
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/traces")

# --- Graph 相关模型 ---
class GraphNode(BaseModel):
    id: str
    label: str
    status: str
    depth: int
    type: str
    signal: Optional[str] = None  # 新增：展示节点是否收到信号

class GraphEdge(BaseModel):
    source: str
    target: str

class TraceGraphResponse(BaseModel):
    trace_id: str
    nodes: List[GraphNode]
    edges: List[GraphEdge]

# --- Summary 相关模型 ---
class TraceSummaryResponse(BaseModel):
    trace_id: str
    total_tasks: int
    status_counts: Dict[str, int]
    max_depth: int          # 新增
    is_cancelled: bool      # 新增
    is_complete: bool       # 新增
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


@router.get("/{trace_id}/tasks", response_model=List[EventInstance])
async def list_tasks_in_trace(
    trace_id: str,
    status: Optional[str] = Query(None),
    actor_type: Optional[str] = Query(None),
    layer: Optional[int] = Query(None),
    depth: Optional[int] = Query(None),  # 新增：适配新的拓扑深度
    role: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0),
    observer_svc: ObserverService = Depends(get_observer_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    多维筛选 trace 内的事件节点。
    支持组合过滤：status + layer + depth + actor_type + role
    """
    filters = {}
    if status: 
        filters["status"] = status
    if actor_type: 
        filters["actor_type"] = actor_type
    if layer is not None: 
        filters["layer"] = layer
    if depth is not None: 
        filters["depth"] = depth  # 新增过滤条件
    if role is not None: 
        filters["role"] = role

    # 使用观察者服务获取事件列表
    trace_instances = await observer_svc.get_trace_instances(session, trace_id)
    
    # 在内存中进行过滤
    filtered_events = []
    for event in trace_instances:
        match = True
        for key, value in filters.items():
            # 注意：getattr 需要确保 EventInstance 模型上有这些字段
            if getattr(event, key, None) != value:
                match = False
                break
        if match:
            filtered_events.append(event)
    
    # 分页
    paginated_events = filtered_events[offset:offset+limit]
    return paginated_events


@router.get("/{trace_id}/graph", response_model=TraceGraphResponse)
async def get_trace_topology(
    trace_id: str,
    observer_svc: ObserverService = Depends(get_observer_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    【新增接口】获取 Trace 的 DAG 拓扑结构。
    用于前端渲染任务执行流图。
    """
    graph_data = await observer_svc.get_trace_graph(session, trace_id)
    if not graph_data:
         raise HTTPException(status_code=404, detail="Trace not found")
    return graph_data


@router.get("/{trace_id}/status", response_model=TraceSummaryResponse)
async def get_trace_status(
    trace_id: str,
    observer_svc: ObserverService = Depends(get_observer_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    获取状态摘要，包含是否被取消、最大深度等扩展信息。
    """
    summary = await observer_svc.get_trace_summary(session, trace_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Trace not found")
    return summary


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    expand_payload: bool = Query(False, description="是否自动拉取并展开 input_ref 指向的大字段数据"),
    observer_svc: ObserverService = Depends(get_observer_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    获取任务详情。
    如果 expand_payload=True，会尝试从 Cache/Storage 拉取原始输入参数。
    """
    # 注意：这里调用的是 Service 中增强后的 get_task_detail
    # 返回值可能是 Dict 而不是 EventInstance 对象，因为 input_params 可能被替换或增强
    task_data = await observer_svc.get_task_detail(
        session,
        task_id,
        fetch_payload=expand_payload
    )
    
    if not task_data:
        raise HTTPException(status_code=404, detail="Task not found")
        
    return task_data


@router.get("/ready-tasks")
async def get_ready_tasks(
    observer_svc: ObserverService = Depends(get_observer_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    获取所有就绪待执行的事件
    """
    ready_events = await observer_svc.get_ready_tasks(session)
    return {
        "count": len(ready_events),
        "tasks": [event.model_dump() for event in ready_events]
    }


@router.websocket("/ws/{trace_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    trace_id: str,
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """
    WebSocket端点，用于前端实时接收trace的动态事件
    前端可以通过此连接获取：
    1. 拓扑结构动态扩展
    2. 任务状态实时变更
    3. 链路取消通知等
    """
    # 建立WebSocket连接
    await connection_manager.connect(websocket, trace_id)
    try:
        # 保持连接，处理心跳或前端指令
        while True:
            # 可选：处理前端发送的消息（当前只读）
            await websocket.receive_text()
    except WebSocketDisconnect:
        # 连接断开，清理资源
        connection_manager.disconnect(websocket, trace_id)
