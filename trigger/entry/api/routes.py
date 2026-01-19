import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timezone

from external.db.session import get_db
from external.db.impl import create_task_definition_repo, create_task_instance_repo, create_scheduled_task_repo
from external.db.session import dialect
from services.lifecycle_service import LifecycleService
from events.event_publisher import event_publisher
from drivers.schedulers.cron_generator import CronGenerator


router = APIRouter()

# 定义 Pydantic 模型
class TaskDefBase(BaseModel):
    name: str
    # 核心字段补全：任务的具体内容（脚本、镜像等）
    content: dict
    
    # 调度策略配置（都是可选的）
    cron_expr: Optional[str] = None
    loop_config: Optional[dict] = None
    
    # 其他元数据
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
    request_id: Optional[str] = None
    user_id: Optional[str] = None

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

# 定义任务触发请求模型
class TaskTriggerRequest(BaseModel):
    input_params: dict = {}
    trigger_type: str = "IMMEDIATE"
    request_id: Optional[str] = None

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
async def create_task_definition(
    task_in: TaskDefCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建任务定义 (Definition)。
    定义可以是：
    1. 定时任务 (传入 cron_expr)
    2. 循环任务 (传入 loop_config)
    3. 手动任务 (不传任何调度配置，仅供 trigger 接口调用)
    """
    def_repo = create_task_definition_repo(db, dialect)
    new_task = await def_repo.create(
        name=task_in.name,
        content=task_in.content,
        cron_expr=task_in.cron_expr,
        loop_config=task_in.loop_config or {},
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
    trigger_req: TaskTriggerRequest = TaskTriggerRequest(),
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """基于已有定义启动任务追踪 (Trace) 和实例 (Instance)"""
    try:
        # [新增] 获取 request_id，如果未提供则自动生成
        request_id = trigger_req.request_id or str(uuid.uuid4())
        
        # 调用start_new_trace，这是基于已有定义启动任务的唯一正规入口
        trace_id = await lifecycle_svc.start_new_trace(
            session=db,
            def_id=def_id,
            input_params=trigger_req.input_params,
            trigger_type=trigger_req.trigger_type,
            request_id=request_id  # [新增] 传入 request_id
        )
        
        return AdHocTaskResponse(
            trace_id=trace_id,
            status="success",
            message=f"Successfully started trace {trace_id} for definition {def_id}"
        )
    except ValueError as e:
        # 处理定义不存在的情况
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ad-hoc-tasks", response_model=AdHocTaskResponse)
async def submit_ad_hoc_task(
    task_in: AdHocTaskRequest,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """提交即席任务，包含定义和实例参数"""
    try:
        # [新增] 获取 request_id，如果未提供则自动生成
        request_id = task_in.request_id or str(uuid.uuid4())
        
        # 调用生命周期服务的即席任务处理方法
        trace_id = await lifecycle_svc.submit_ad_hoc_task(
            session=db,
            task_name=task_in.task_name,
            task_content=task_in.task_content,
            input_params=task_in.input_params,
            loop_config=task_in.loop_config,
            is_temporary=task_in.is_temporary,
            schedule_type=task_in.schedule_type,
            schedule_config=task_in.schedule_config,
            request_id=request_id,  # [新增] 传入 request_id
            user_id=task_in.user_id  # [新增] 传入 user_id
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


@router.post("/traces/{trace_id}/pause", response_model=TaskControlResponse)
async def pause_trace_tasks(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """暂停指定trace下的所有任务实例"""
    result = await lifecycle_svc.pause_task(
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


@router.post("/traces/{trace_id}/resume", response_model=TaskControlResponse)
async def resume_trace_tasks(
    trace_id: str,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """继续指定trace下的所有任务实例"""
    result = await lifecycle_svc.resume_task(
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


@router.patch("/traces/{trace_id}/modify", response_model=TaskControlResponse)
async def modify_trace_tasks(
    trace_id: str,
    task_modify: TaskModifyRequest,
    db: AsyncSession = Depends(get_db),
    lifecycle_svc: LifecycleService = Depends(get_lifecycle_service)
):
    """修改指定trace下的所有任务实例"""
    result = await lifecycle_svc.modify_task(
        session=db,
        trace_id=trace_id,
        input_params=task_modify.input_params,
        schedule_config=task_modify.schedule_config
    )
    return TaskControlResponse(
        success=result["success"],
        message=result["message"],
        details={
            "trace_id": trace_id,
            "affected_instances": result.get("affected_instances", []),
            "failed_instances": result.get("failed_instances", []),
            **result.get("details", {})
        }
    )


@router.get("/request-id-to-trace/{request_id}")
async def request_id_to_trace(
    request_id: str
):
    """根据request_id获取最新的trace_id"""
    trace_id = await event_publisher.get_latest_trace_by_request(request_id=request_id)
    if trace_id:
        return {
            "success": True,
            "trace_id": trace_id,
            "message": f"Successfully retrieved trace_id for request_id {request_id}"
        }
    else:
        return {
            "success": False,
            "trace_id": None,
            "message": f"No trace_id found for request_id {request_id}"
        }


# ============== 新增：任务定义和调度任务管理 API ==============

class TaskDefinitionUpdateRequest(BaseModel):
    """任务定义更新请求"""
    cron_expr: Optional[str] = None
    loop_config: Optional[dict] = None
    schedule_config: Optional[dict] = None
    is_active: Optional[bool] = None
    content: Optional[dict] = None


class ScheduledTaskRescheduleRequest(BaseModel):
    """调度任务重新调度请求"""
    scheduled_time: datetime
    schedule_config: Optional[dict] = None


class ScheduledTaskUpdateRequest(BaseModel):
    """调度任务更新请求"""
    scheduled_time: Optional[datetime] = None
    schedule_config: Optional[dict] = None
    input_params: Optional[dict] = None
    priority: Optional[int] = None


class ScheduledTaskResponse(BaseModel):
    """调度任务响应"""
    id: str
    definition_id: str
    trace_id: str
    status: str
    schedule_type: str
    scheduled_time: datetime
    round_index: int
    input_params: Optional[dict] = None
    error_msg: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.patch("/definitions/{def_id}", response_model=TaskDefResponse)
async def update_task_definition(
    def_id: str,
    update_req: TaskDefinitionUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    更新任务定义

    支持修改：
    - cron_expr: CRON 表达式（会验证格式）
    - loop_config: 循环配置
    - schedule_config: 调度配置
    - is_active: 是否激活
    - content: 任务内容
    """
    def_repo = create_task_definition_repo(db, dialect)

    # 检查定义是否存在
    existing = await def_repo.get(def_id)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Task definition {def_id} not found")

    # 验证 CRON 表达式
    if update_req.cron_expr is not None and update_req.cron_expr != "":
        if not CronGenerator.is_valid_cron(update_req.cron_expr):
            raise HTTPException(status_code=400, detail=f"Invalid CRON expression: {update_req.cron_expr}")

    # 构建更新参数
    update_params = {}
    if update_req.cron_expr is not None:
        update_params["cron_expr"] = update_req.cron_expr if update_req.cron_expr else None
    if update_req.loop_config is not None:
        update_params["loop_config"] = update_req.loop_config
    if update_req.schedule_config is not None:
        update_params["schedule_config"] = update_req.schedule_config
    if update_req.is_active is not None:
        update_params["is_active"] = update_req.is_active
    if update_req.content is not None:
        update_params["content"] = update_req.content

    if not update_params:
        return existing

    updated = await def_repo.update(def_id, **update_params)
    return updated


@router.get("/definitions/{def_id}", response_model=TaskDefResponse)
async def get_task_definition(
    def_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个任务定义"""
    def_repo = create_task_definition_repo(db, dialect)
    definition = await def_repo.get(def_id)
    if not definition:
        raise HTTPException(status_code=404, detail=f"Task definition {def_id} not found")
    return definition


@router.get("/scheduled-tasks/{task_id}", response_model=ScheduledTaskResponse)
async def get_scheduled_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取单个调度任务"""
    repo = create_scheduled_task_repo(db, dialect)
    task = await repo.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Scheduled task {task_id} not found")
    return task


@router.patch("/scheduled-tasks/{task_id}", response_model=ScheduledTaskResponse)
async def update_scheduled_task(
    task_id: str,
    update_req: ScheduledTaskUpdateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    更新调度任务

    只允许修改 PENDING 状态的任务

    支持修改：
    - scheduled_time: 调度时间
    - schedule_config: 调度配置
    - input_params: 输入参数
    - priority: 优先级
    """
    repo = create_scheduled_task_repo(db, dialect)

    # 构建更新参数
    update_params = {}
    if update_req.scheduled_time is not None:
        update_params["scheduled_time"] = update_req.scheduled_time
    if update_req.schedule_config is not None:
        update_params["schedule_config"] = update_req.schedule_config
    if update_req.input_params is not None:
        update_params["input_params"] = update_req.input_params
    if update_req.priority is not None:
        update_params["priority"] = update_req.priority

    if not update_params:
        task = await repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Scheduled task {task_id} not found")
        return task

    try:
        updated = await repo.update_scheduled_task(task_id, **update_params)
        if not updated:
            raise HTTPException(status_code=404, detail=f"Scheduled task {task_id} not found")
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scheduled-tasks/{task_id}/reschedule", response_model=ScheduledTaskResponse)
async def reschedule_task(
    task_id: str,
    reschedule_req: ScheduledTaskRescheduleRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    重新调度任务

    将任务状态重置为 PENDING，并更新调度时间
    只允许对 FAILED、CANCELLED、SUCCESS 状态的任务进行重新调度
    """
    repo = create_scheduled_task_repo(db, dialect)

    try:
        rescheduled = await repo.reschedule_task(
            task_id=task_id,
            new_scheduled_time=reschedule_req.scheduled_time,
            new_schedule_config=reschedule_req.schedule_config
        )
        if not rescheduled:
            raise HTTPException(status_code=404, detail=f"Scheduled task {task_id} not found")
        return rescheduled
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/scheduled-tasks/{task_id}/cancel", response_model=TaskControlResponse)
async def cancel_scheduled_task(
    task_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    取消调度任务

    只允许取消 PENDING 或 SCHEDULED 状态的任务
    """
    repo = create_scheduled_task_repo(db, dialect)

    success = await repo.cancel_task(task_id)
    if success:
        return TaskControlResponse(
            success=True,
            message=f"Successfully cancelled scheduled task {task_id}",
            details={"task_id": task_id}
        )
    else:
        # 检查任务是否存在
        task = await repo.get(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Scheduled task {task_id} not found")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot cancel task in {task.status} status. Only PENDING or SCHEDULED tasks can be cancelled."
            )


