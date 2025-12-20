from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
from .base import ExecutionStatus, ExecutionLogEntry
from .task_draft import ScheduleDTO

class TaskExecutionContextDTO(BaseModel):
    """⚙️ [4. TaskExecutionContextDTO] 任务执行上下文"""
    task_id: str = Field(default_factory=lambda: str(uuid4())) # 正式ID
    draft_id: str          # 关联的草稿ID
    task_type: str
    
    # 最终用于执行的参数 (来自 Draft.slots.resolved)
    parameters: Dict[str, Any] = Field(default_factory=dict)

    # 执行状态
    execution_status: ExecutionStatus = ExecutionStatus.NOT_STARTED
    
    # --- 中断与恢复支持 ---
    awaiting_input_for: Optional[str] = None  # 当前等待哪个字段？如 "captcha"
    interruption_message: Optional[str] = None # 如 "请输入验证码"
    last_checkpoint: Optional[str] = None     # 断点位置
    
    # 调度信息（继承自草稿）
    schedule: Optional[ScheduleDTO] = None

    # 控制状态
    control_status: str  # 'NORMAL' | 'PAUSED' | 'CANCELLED_BY_USER' | 'TERMINATED'

    # 关联的父任务（用于循环任务：每次执行是一个子实例）
    parent_task_id: Optional[str] = None
    run_index: Optional[int] = None          # 第几次运行（循环任务）

    # 查询优化字段
    title: str                  # 任务标题（便于展示）
    tags: List[str] = Field(default_factory=list)        # 标签（如 ["爬虫", "日报"]）
    created_by: str             # 创建者 ID
    created_at: datetime = Field(default_factory=datetime.now) # 创建时间

    # 日志与结果
    logs: List[ExecutionLogEntry] = Field(default_factory=list)
    result_data: Optional[Dict[str, Any]] = None # 执行成功后的结果
    error_detail: Optional[Dict[str, Any]] = None # 错误信息
    
    # 外部执行系统关联
    external_job_id: Optional[str] = None # 外部执行系统的任务ID

class TaskControlResponseDTO(BaseModel):
    """任务控制操作的统一响应对象"""
    success: bool
    message: str
    task_id: Optional[str] = None
    operation: Optional[str] = None  # 例如: "PAUSE", "CANCEL", "RETRY"
    data: Dict[str, Any] = Field(default_factory=dict)  # 承载外部客户端返回的原始数据

    @classmethod
    def success_result(cls, message: str, task_id: str, operation: str, data: Dict[str, Any] = None) -> 'TaskControlResponseDTO':
        """快速构建成功响应"""
        return cls(
            success=True,
            message=message,
            task_id=task_id,
            operation=operation,
            data=data or {}
        )

    @classmethod
    def error_result(cls, message: str, task_id: Optional[str] = None, operation: Optional[str] = None) -> 'TaskControlResponseDTO':
        """快速构建失败响应"""
        return cls(
            success=False,
            message=message,
            task_id=task_id,
            operation=operation
        )
        
    def to_dict(self) -> Dict[str, Any]:
        """兼容旧版接口，转换为字典"""
        return {
            "success": self.success,
            "message": self.message,
            "task_id": self.task_id,
            "operation": self.operation,
            "data": self.data
        }