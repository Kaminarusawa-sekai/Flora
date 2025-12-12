from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

from .task_control_service import task_control_service
from .task_models import TaskTriggerType, TaskStatus, TaskDefinition, TaskInstance

# 创建FastAPI应用
app = FastAPI(title="Task Control Service API", description="全功能任务中台服务")

# 请求模型
class CreateTaskRequest(BaseModel):
    user_id: str
    content: str
    trigger_type: TaskTriggerType
    trigger_args: Optional[Dict[str, Any]] = None

class TaskInstanceResponse(BaseModel):
    instance_id: str
    task_def_id: str
    content: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error: Optional[str]

class TaskDefinitionResponse(BaseModel):
    task_def_id: str
    user_id: str
    content: str
    trigger_type: TaskTriggerType
    trigger_args: Optional[Dict[str, Any]]
    status: TaskStatus
    created_at: datetime
    updated_at: datetime

# 路由
@app.post("/tasks", response_model=str, summary="创建任务")
async def create_task(request: CreateTaskRequest):
    """
    创建一个新任务
    
    - **user_id**: 用户ID
    - **content**: 任务内容
    - **trigger_type**: 触发类型 (IMMEDIATE, SCHEDULED, LOOP)
    - **trigger_args**: 触发参数
      - 对于 IMMEDIATE: 不需要额外参数
      - 对于 SCHEDULED: 需要 run_date (datetime)
      - 对于 LOOP: 需要 interval (秒) 或 cron (表达式)
    """
    try:
        task_def_id = task_control_service.create_task(
            user_id=request.user_id,
            content=request.content,
            trigger_type=request.trigger_type,
            trigger_args=request.trigger_args
        )
        return task_def_id
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/tasks/{task_def_id}/pause", summary="暂停任务调度")
async def pause_task(task_def_id: str):
    """
    暂停任务调度（不影响正在运行的实例）
    """
    try:
        task_control_service.pause_schedule(task_def_id)
        return {"message": f"Task {task_def_id} paused"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/tasks/{task_def_id}/resume", summary="恢复任务调度")
async def resume_task(task_def_id: str):
    """
    恢复任务调度
    """
    try:
        task_control_service.resume_schedule(task_def_id)
        return {"message": f"Task {task_def_id} resumed"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/tasks/{task_def_id}/cancel", summary="取消任务")
async def cancel_task(task_def_id: str):
    """
    彻底取消任务，包括移除调度和终止运行中的实例
    """
    try:
        task_control_service.cancel_task(task_def_id)
        return {"message": f"Task {task_def_id} cancelled"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/tasks/{task_def_id}/trigger", summary="手动触发任务")
async def trigger_task(task_def_id: str):
    """
    手动触发一次任务执行（立即执行）
    """
    try:
        task_control_service.trigger_immediately(task_def_id)
        return {"message": f"Task {task_def_id} triggered immediately"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/tasks/{task_def_id}", response_model=TaskDefinitionResponse, summary="获取任务定义")
async def get_task_definition(task_def_id: str):
    """
    获取任务定义详情
    """
    task_def = task_control_service.get_task_definition(task_def_id)
    if not task_def:
        raise HTTPException(status_code=404, detail=f"Task {task_def_id} not found")
    return task_def

@app.get("/tasks/{task_def_id}/instances", response_model=List[TaskInstanceResponse], summary="获取任务实例列表")
async def get_task_instances(task_def_id: str):
    """
    获取任务的所有执行实例
    """
    instances = task_control_service.get_task_instances(task_def_id)
    return instances

@app.get("/users/{user_id}/tasks", response_model=List[TaskDefinitionResponse], summary="获取用户任务列表")
async def get_user_tasks(user_id: str):
    """
    获取用户的所有任务定义
    """
    tasks = task_control_service.get_user_tasks(user_id)
    return tasks

# 启动服务
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)