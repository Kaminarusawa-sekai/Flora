from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timezone

from ...external.db.session import get_db
from ...external.db.impl import create_task_definition_repo, create_task_instance_repo
from ...external.db.session import dialect
from ...services.lifecycle_service import LifecycleService

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

@router.get("/definitions/{def_id}", response_model=TaskDefResponse)
async def get_task_definition(
    def_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个任务定义"""
    def_repo = create_task_definition_repo(db, dialect)
    task_def = await def_repo.get(def_id)
    if not task_def:
        raise HTTPException(status_code=404, detail="Task definition not found")
    return task_def

@router.post("/definitions/{def_id}/trigger")
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
    await lifecycle_svc.start_new_trace(
        session=db,
        def_id=def_id,
        input_params={"trigger": "manual"},
        trigger_type="MANUAL"
    )
    return {"status": "triggered", "message": f"Task {def_id} triggered manually"}

@router.get("/instances/{trace_id}", response_model=List[TaskInstanceResponse])
async def get_task_instances(
    trace_id: str,
    db: AsyncSession = Depends(get_db)
):
    """查询某个 Trace 下的所有任务实例状态"""
    instance_repo = create_task_instance_repo(db, dialect)
    instances = await instance_repo.list_by_trace_id(trace_id)
    return instances

@router.get("/instances/{trace_id}/status")
async def get_trace_status(
    trace_id: str,
    db: AsyncSession = Depends(get_db)
):
    """查询某个 Trace 的整体状态"""
    instance_repo = create_task_instance_repo(db, dialect)
    instances = await instance_repo.list_by_trace_id(trace_id)
    
    if not instances:
        raise HTTPException(status_code=404, detail="No instances found for this trace")
    
    # 计算整体状态
    statuses = [inst.status for inst in instances]
    if "FAILED" in statuses:
        overall_status = "FAILED"
    elif "RUNNING" in statuses:
        overall_status = "RUNNING"
    elif all(status == "SUCCESS" for status in statuses):
        overall_status = "SUCCESS"
    else:
        overall_status = "PENDING"
    
    return {
        "trace_id": trace_id,
        "status": overall_status,
        "instance_count": len(instances),
        "instance_statuses": {
            "PENDING": statuses.count("PENDING"),
            "RUNNING": statuses.count("RUNNING"),
            "SUCCESS": statuses.count("SUCCESS"),
            "FAILED": statuses.count("FAILED")
        }
    }
