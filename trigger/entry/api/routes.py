from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timezone

from external.db.session import get_db
from external.db.impl import create_task_definition_repo, create_task_instance_repo
from external.db.session import dialect
from services.lifecycle_service import LifecycleService

router = APIRouter()

# 定义 Pydantic 模型
class TaskDefBase(BaseModel):
    name: str
    cron_expr: Optional[str] = None
    loop_config: dict = {}
    is_active: bool = True

class TaskDefCreate(TaskDefBase):
    pass

class TaskDefResponse(TaskDefBase):
    id: str
    last_triggered_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class TaskInstanceResponse(BaseModel):
    id: str
    definition_id: str
    trace_id: str
    status: str
    schedule_type: str
    round_index: int
    input_params: dict
    output_ref: Optional[str] = None
    error_msg: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

# 定义即席任务请求模型
class AdHocTaskRequest(BaseModel):
    task_name: str
    task_content: dict  # 具体的执行逻辑，如 {"script": "print('hello')", "image": "python:3.9"}
    input_params: dict
    loop_config: Optional[dict] = None
    is_temporary: bool = True
    schedule_type: str = "IMMEDIATE"  # 调度类型：IMMEDIATE, CRON, LOOP, DELAYED
    schedule_config: Optional[dict] = None  # 调度配置，根据schedule_type不同而不同
    # - IMMEDIATE/ONCE: 无需配置
    # - CRON: 需包含 {"cron_expression": "* * * * *"} (cron表达式)
    # - DELAYED: 需包含 {"delay_seconds": 60} (延迟秒数)
    # - LOOP: 使用loop_config字段配置，schedule_config可不传

# 定义即席任务响应模型
class AdHocTaskResponse(BaseModel):
    trace_id: str
    status: str
    message: str

# 任务控制相关的 Pydantic 模型
class TaskControlResponse(BaseModel):
    success: bool
    message: str
    details: Optional[dict] = None

class TaskModifyRequest(BaseModel):
    input_params: Optional[dict] = None
    schedule_config: Optional[dict] = None

# 全局服务变量，将在 main.py 中初始化
_lifecycle_svc = None

def set_lifecycle_service(service: LifecycleService):
    """设置生命周期服务实例"""
    global _lifecycle_svc
    _lifecycle_svc = service

async def get_lifecycle_service():
    """获取生命周期服务实例"""
    if not _lifecycle_svc:
        raise HTTPException(status_code=500, detail="Lifecycle service not initialized")
    return _lifecycle_svc

@router.post("/definitions", response_model=TaskDefResponse)
async def create_cron_task(
    task_in: TaskDefCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建一个新的定时任务定义"""
    def_repo = create_task_definition_repo(db, dialect)
    new_task = await def_repo.create(
        name=task_in.name,
        cron_expr=task_in.cron_expr,
        loop_config=task_in.loop_config,
        is_active=task_in.is_active
    )
    return new_task

@router.get("/definitions", response_model=List[TaskDefResponse])
async def list_task_definitions(
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取任务定义列表"""
    def_repo = create_task_definition_repo(db, dialect)
    # 这里简化处理，实际应该根据 is_active 参数过滤
    active_defs = await def_repo.list_active_cron()
    return active_defs


@router.post("/definitions/{def_id}/trigger", response_model=AdHocTaskResponse)
async def manual_trigger(
    def_id: str,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """手动触发一次任务 (不等待 CRON)"""
    # 检查任务定义是否存在
    def_repo = create_task_definition_repo(db, dialect)
    task_def = await def_repo.get(def_id)
    if not task_def:
        raise HTTPException(status_code=404, detail="Task definition not found")
    
    # 手动触发任务
    task_id = await lifecycle_svc.trigger_by_id(
        session=db,
        def_id=def_id,
        input_params={"trigger": "manual"}
    )
    
    return AdHocTaskResponse(
        trace_id=task_id,
        status="success",
        message=f"Task {def_id} triggered manually with task ID {task_id}"
    )


@router.post("/ad-hoc-tasks", response_model=AdHocTaskResponse)
async def submit_ad_hoc_task(
    task_in: AdHocTaskRequest,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """提交即席任务，包含定义和实例参数"""
    try:
        # 调用生命周期服务的即席任务处理方法
        trace_id = await lifecycle_svc.submit_ad_hoc_task(
            session=db,
            task_name=task_in.task_name,
            task_content=task_in.task_content,
            input_params=task_in.input_params,
            loop_config=task_in.loop_config,
            is_temporary=task_in.is_temporary,
            schedule_type=task_in.schedule_type,
            schedule_config=task_in.schedule_config
        )
        
        if not trace_id:
            raise HTTPException(status_code=500, detail="Failed to create ad-hoc task")
        
        return AdHocTaskResponse(
            trace_id=trace_id,
            status="success",
            message=f"Ad-hoc task submitted successfully with trace ID {trace_id}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error submitting ad-hoc task: {str(e)}")


# 任务控制相关的 API 端点
@router.post("/instances/{instance_id}/cancel", response_model=TaskControlResponse)
async def cancel_task(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """取消指定的任务实例"""
    result = await lifecycle_svc.cancel_task(
        session=db,
        instance_id=instance_id
    )
    return TaskControlResponse(
        success=result["success"],
        message=result["message"],
        details={
            "instance_id": instance_id,
            **result.get("details", {})
        }
    )


@router.post("/traces/{trace_id}/cancel", response_model=TaskControlResponse)
async def cancel_trace_tasks(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """取消指定trace下的所有任务实例"""
    result = await lifecycle_svc.cancel_task(
        session=db,
        trace_id=trace_id
    )
    return TaskControlResponse(
        success=result["success"],
        message=result["message"],
        details={
            "trace_id": trace_id,
            "affected_instances": result.get("affected_instances", []),
            "failed_instances": result.get("failed_instances", [])
        }
    )


@router.post("/instances/{instance_id}/pause", response_model=TaskControlResponse)
async def pause_task(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """暂停指定的任务实例"""
    result = await lifecycle_svc.pause_task(
        session=db,
        instance_id=instance_id
    )
    return TaskControlResponse(
        success=result["success"],
        message=result["message"],
        details=result.get("details", {})
    )


@router.post("/instances/{instance_id}/resume", response_model=TaskControlResponse)
async def resume_task(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """继续指定的任务实例"""
    result = await lifecycle_svc.resume_task(
        session=db,
        instance_id=instance_id
    )
    return TaskControlResponse(
        success=result["success"],
        message=result["message"],
        details=result.get("details", {})
    )


@router.patch("/instances/{instance_id}/modify", response_model=TaskControlResponse)
async def modify_task(
    instance_id: str,
    task_modify: TaskModifyRequest,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """修改指定的任务实例"""
    result = await lifecycle_svc.modify_task(
        session=db,
        instance_id=instance_id,
        input_params=task_modify.input_params,
        schedule_config=task_modify.schedule_config
    )
    return TaskControlResponse(
        success=result["success"],
        message=result["message"],
        details=result.get("details", {})
    )


