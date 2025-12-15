from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import asyncio

# 仅在直接运行时才尝试导入uvicorn，避免依赖问题
try:
    import uvicorn
    HAS_UVICORN = True
except ImportError:
    HAS_UVICORN = False
    uvicorn = None

# 导入指令塔核心模块
from events.command_tower import (
    TaskRegistrar,
    SignalController,
    EventProcessor,
    DAGDispatcherCoordinator,
    TaskObserver,
    LifecycleManager,
    CronScheduler,
    LoopController
)

# 创建FastAPI应用
app = FastAPI(
    title="指令塔API服务",
    version="1.0.0",
    description="指令塔核心功能API，提供任务管理、控制和观察能力"
)

# 依赖注入：实际应用中应使用依赖注入框架
# 这里简化处理，使用模拟的客户端
class MockDBClient:
    def get_task(self, task_id):
        return None
    def bulk_insert(self, tasks):
        return None
    def get_last_scheduled_run(self, definition_id):
        return None
    def insert_scheduled_run(self, run):
        return None
    def query(self, sql, *args):
        return []
    def count_tasks(self, trace_id):
        return 0
    def count_completed_tasks(self, trace_id):
        return 0

class MockRedisClient:
    def hset(self, key, field, value):
        return None
    def hget(self, key, field):
        return None
    def delete(self, key):
        return None

# 初始化模拟客户端
mock_db = MockDBClient()
mock_redis = MockRedisClient()

# 初始化指令塔核心组件
task_registrar = TaskRegistrar(mock_db)
signal_controller = SignalController(mock_redis, mock_db)
event_processor = EventProcessor(mock_db)
dag_dispatcher = DAGDispatcherCoordinator(mock_db)
task_observer = TaskObserver(mock_db)
lifecycle_manager = LifecycleManager(mock_db, task_registrar)
cron_scheduler = CronScheduler(mock_db, lifecycle_manager)
loop_controller = LoopController(mock_db, task_registrar)

# --- 数据模型定义 --- 

class Priority(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

class RunTaskRequest(BaseModel):
    job_id: str
    input_params: Dict[str, Any]
    priority: Optional[Priority] = Priority.MEDIUM
    tags: Optional[List[str]] = Field(default_factory=list)

class LoopTaskRequest(BaseModel):
    job_id: str
    input_params: Dict[str, Any]
    loop_config: Dict[str, Any]

class CancelRequest(BaseModel):
    reason: Optional[str] = "user_request"
    force: bool = False

class TaskDefinitionRequest(BaseModel):
    name: str
    actor_type: str
    code_ref: str
    schedule_type: str
    resource_profile: str = "default"
    default_params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    is_active: bool = True

class ScheduleRequest(BaseModel):
    job_id: str
    cron_expr: str
    input_params: Optional[Dict[str, Any]] = Field(default_factory=dict)
    enabled: bool = True

class TaskRunResponse(BaseModel):
    trace_id: str
    root_task_id: str
    status: str

# --- API端点实现 --- 

# 一、任务启动类 API

@app.post("/v1/tasks/run", response_model=TaskRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_task(request: RunTaskRequest):
    """
    启动一次性任务
    """
    # 生成唯一trace_id和root_task_id
    trace_id = f"run_{datetime.utcnow().timestamp()}"
    root_task_id = f"task_root_{trace_id}"
    
    # 实际应用中应调用lifecycle_manager.start_root_task()
    # 这里简化处理，直接返回模拟结果
    return TaskRunResponse(
        trace_id=trace_id,
        root_task_id=root_task_id,
        status="PENDING"
    )

@app.post("/v1/tasks/loop", response_model=TaskRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_loop_task(request: LoopTaskRequest):
    """
    启动循环任务（带退出条件）
    """
    # 生成唯一trace_id和root_task_id
    trace_id = f"loop_{datetime.utcnow().timestamp()}"
    root_task_id = f"task_root_{trace_id}"
    
    # 实际应用中应调用lifecycle_manager.start_root_task()
    # 这里简化处理，直接返回模拟结果
    return TaskRunResponse(
        trace_id=trace_id,
        root_task_id=root_task_id,
        status="PENDING"
    )

# 二、任务控制类 API

@app.post("/v1/tasks/{trace_id}/cancel", status_code=status.HTTP_202_ACCEPTED)
def cancel_task(trace_id: str, request: Optional[CancelRequest] = None):
    """
    取消任务（整棵树）
    """
    # 实际应用中应调用signal_controller.process_control_event()
    # 这里简化处理，直接返回成功
    return {"status": "accepted", "message": f"Cancel request for {trace_id} received"}

@app.post("/v1/tasks/{trace_id}/pause", status_code=status.HTTP_202_ACCEPTED)
def pause_task(trace_id: str):
    """
    暂停任务
    """
    # 实际应用中应调用signal_controller.process_control_event()
    return {"status": "accepted", "message": f"Pause request for {trace_id} received"}

@app.post("/v1/tasks/{trace_id}/resume", status_code=status.HTTP_202_ACCEPTED)
def resume_task(trace_id: str):
    """
    恢复任务
    """
    # 实际应用中应调用signal_controller.clear_signal()
    return {"status": "accepted", "message": f"Resume request for {trace_id} received"}

# 三、任务查询类 API

@app.get("/v1/tasks/{trace_id}/tree")
def get_task_tree(trace_id: str):
    """
    获取任务树（完整拓扑）
    """
    # 实际应用中应调用task_observer.get_task_tree()
    # 这里返回模拟数据
    return {
        "trace_id": trace_id,
        "root": {
            "id": "T0",
            "job_id": "strategy_router",
            "role": "root",
            "layer": 0,
            "status": "RUNNING",
            "children": [
                {
                    "id": "G1",
                    "actor_type": "GROUP_AGG",
                    "role": "fundamental_pipeline",
                    "layer": 1,
                    "children": [
                        {
                            "id": "S1",
                            "actor_type": "SINGLE_AGG",
                            "layer": 2,
                            "children": [
                                { "id": "A1", "actor_type": "AGENT", "layer": 3, "is_leaf_agent": True },
                                { "id": "E1", "actor_type": "EXECUTION", "layer": 4 }
                            ]
                        }
                    ]
                }
            ]
        },
        "progress": 65.5,
        "created_at": "2025-12-12T10:00:00Z"
    }

@app.get("/v1/tasks/{trace_id}/summary")
def get_task_summary(trace_id: str):
    """
    获取任务状态摘要（轻量级）
    """
    # 实际应用中应调用task_observer.get_task_statistics()
    # 这里返回模拟数据
    return {
        "trace_id": trace_id,
        "status": "RUNNING",
        "total_tasks": 12,
        "completed_tasks": 8,
        "failed_tasks": 1,
        "cancelled_tasks": 0,
        "progress_percent": 66.7,
        "current_layer": 3,
        "running_roles": ["data_fetcher", "validator"],
        "last_updated": "2025-12-12T10:05:23Z"
    }

@app.get("/v1/tasks/{trace_id}/events")
async def get_task_events(trace_id: str):
    """
    流式事件订阅（WebSocket/SSE）
    """
    async def event_generator():
        # 模拟事件流
        events = [
            { "event": "TASK_STARTED", "task_id": "E1", "timestamp": 1734567890 },
            { "event": "TASK_COMPLETED", "task_id": "E1", "output_ref": "s3://..." },
            { "event": "PROGRESS", "progress": 75.2 },
            { "event": "TASK_FAILED", "task_id": "S2", "error": "Timeout" }
        ]
        
        for event in events:
            yield f"data: {str(event)}\n\n"
            await asyncio.sleep(1)
    
    return StreamingResponse(event_generator(), media_type="text/event-stream")

# 四、任务定义管理 API

@app.put("/v1/definitions/{job_id}")
def register_definition(job_id: str, request: TaskDefinitionRequest):
    """
    注册/更新任务模板
    """
    return {"status": "success", "message": f"Definition {job_id} updated"}

@app.get("/v1/definitions")
def list_definitions(active: Optional[bool] = None, tags: Optional[str] = None):
    """
    列出所有任务定义
    """
    return {"definitions": [], "total": 0}

# 五、定时任务管理 API

@app.put("/v1/schedules/{schedule_name}")
def create_schedule(schedule_name: str, request: ScheduleRequest):
    """
    创建/更新定时任务
    """
    return {"status": "success", "message": f"Schedule {schedule_name} updated"}

@app.get("/v1/schedules/{schedule_name}/runs")
def get_schedule_runs(schedule_name: str, limit: int = 10):
    """
    查询定时任务运行历史
    """
    return [
        {"trace_id": "run_abc", "scheduled_at": "2025-12-11T02:00:00Z", "status": "SUCCESS"},
        {"trace_id": "run_def", "status": "FAILED", "error": "Connection timeout"}
    ]

# 六、循环任务控制 API

@app.post("/v1/tasks/{trace_id}/stop_loop", status_code=status.HTTP_202_ACCEPTED)
def stop_loop(trace_id: str):
    """
    提前终止循环
    """
    return {"status": "accepted", "message": f"Stop loop request for {trace_id} received"}

# 七、系统级 API

@app.get("/health")
def health_check():
    """
    健康检查
    """
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

@app.get("/metrics")
def get_metrics():
    """
    统计指标（Prometheus 格式）
    """
    metrics = """
# HELP task_instances_total Total number of task instances
# TYPE task_instances_total gauge
task_instances_total{status="RUNNING"} 5
# HELP task_event_queue_length Length of task event queue
# TYPE task_event_queue_length gauge
task_event_queue_length 0
# HELP dispatcher_assign_rate Rate of task assignments by dispatcher
# TYPE dispatcher_assign_rate counter
dispatcher_assign_rate 10
"""
    return StreamingResponse(content=metrics, media_type="text/plain")

# 启动服务（开发环境）
if __name__ == "__main__":
    if HAS_UVICORN:
        uvicorn.run(
            "api_service:app",
            host="0.0.0.0",
            port=8000,
            reload=True
        )
    else:
        print("Uvicorn not installed, skipping service startup. To run the service, install uvicorn with: pip install uvicorn")
