from fastapi import APIRouter, Query, HTTPException, Depends, WebSocket, WebSocketDisconnect
from typing import List, Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel

# 导入依赖注入
from ..deps import get_observer_service, get_db_session, get_connection_manager, get_agent_monitor_service
from services.observer_service import ObserverService
from services.agent_monitor_service import AgentMonitorService
from services.websocket_manager import ConnectionManager
from common.event_instance import EventInstance
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


class TraceByUserResponse(BaseModel):
    """单个trace的用户查询响应模型"""
    trace_id: str
    created_at: datetime
    status: str


class TraceListByUserResponse(BaseModel):
    """用户trace列表响应模型"""
    user_id: str
    count: int
    traces: List[TraceByUserResponse]


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


@router.get("/{trace_id}/trace-details")
async def get_trace_detail(
    trace_id: str,
    expand_payload: bool = Query(False, description="是否自动拉取并展开 input_ref 指向的大字段数据"),
    observer_svc: ObserverService = Depends(get_observer_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    获取指定trace_id下的所有任务详情。
    如果 expand_payload=True，会尝试从 Cache/Storage 拉取原始输入参数。
    """
    # 注意：这里调用的是 Service 中增强后的 get_task_detail
    # 返回值是 Dict 列表，包含了每个任务的详细信息和可能的扩展数据
    task_data = await observer_svc.get_trace_detail(
        session,
        trace_id,
        fetch_payload=expand_payload
    )
    
    if not task_data:
        return []
        
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


@router.get("/by-user/{user_id}", response_model=TraceListByUserResponse)
async def get_traces_by_user_id(
    user_id: str,
    start_time: Optional[datetime] = Query(None, description="开始时间"),
    end_time: Optional[datetime] = Query(None, description="结束时间"),
    limit: int = Query(100, le=1000, description="每页数量"),
    offset: int = Query(0, description="偏移量"),
    observer_svc: ObserverService = Depends(get_observer_service),
    session: AsyncSession = Depends(get_db_session)
):
    """
    根据user_id查询所有trace_id及其状态，支持时间范围过滤和分页
    """
    traces = await observer_svc.find_traces_by_user_id(
        session=session,
        user_id=user_id,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset
    )
    
    return {
        "user_id": user_id,
        "count": len(traces),
        "traces": traces
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


@router.websocket("/ws/agent/{agent_id}")
async def agent_tree_websocket(
    websocket: WebSocket,
    agent_id: str,
    agent_monitor_service: AgentMonitorService = Depends(get_agent_monitor_service),
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """
    WebSocket端点，用于实时获取Agent动态树数据
    前端可以通过此连接获取：
    1. Agent树的静态结构
    2. Agent的运行时状态
    3. Agent状态的实时更新
    """
    # 建立WebSocket连接
    await connection_manager.connect(websocket, f"agent:{agent_id}")
    try:
        # 初始发送Agent动态树数据
        dynamic_tree = await agent_monitor_service.get_dynamic_agent_tree(agent_id)
        await websocket.send_json(dynamic_tree)
        
        # 保持连接，处理心跳或前端指令
        while True:
            # 接收前端消息，支持刷新树数据等指令
            message = await websocket.receive_text()
            if message == "refresh":
                # 刷新Agent动态树数据
                dynamic_tree = await agent_monitor_service.get_dynamic_agent_tree(agent_id)
                await websocket.send_json(dynamic_tree)
    except WebSocketDisconnect:
        # 连接断开，清理资源
        connection_manager.disconnect(websocket, f"agent:{agent_id}")
