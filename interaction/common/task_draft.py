from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from uuid import uuid4
from enum import Enum
from .base import SlotSource

class TaskDraftStatus(str, Enum):
    FILLING = "FILLING"           # 填槽中
    PENDING_CONFIRM = "PENDING_CONFIRM" # 待确认
    SUBMITTED = "SUBMITTED"       # 已提交/进入执行
    CANCELLED = "CANCELLED"       # 已取消

class SlotValueDTO(BaseModel):
    """槽位详细状态"""
    raw: str                  # 用户原始说法
    resolved: Any             # 解析后标准值
    confirmed: bool = False   # 是否已确认
    source: SlotSource = SlotSource.USER

class ScheduleDTO(BaseModel):
    """调度信息（用于定时/循环任务）"""
    type: str  # 'ONCE' | 'RECURRING' 一次性 or 循环
    cron_expression: Optional[str] = None  # 标准 cron（可选）
    natural_language: Optional[str] = None  # 用户原始说法：“每天早上8点”
    next_trigger_time: Optional[float] = None  # 下次触发时间戳
    timezone: Optional[str] = None  # 时区（如 "Asia/Shanghai"）
    max_runs: Optional[int] = None  # 最大执行次数（循环任务用）
    end_time: Optional[float] = None  # 循环结束时间

class TaskDraftDTO(BaseModel):
    """📝 [3. TaskDraftDTO] 任务草稿"""
    draft_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str            # 所属用户ID
    task_type: str          # 如 "CRAWLER", "BOOKING"
    
    # 状态流转：FILLING -> PENDING_CONFIRM -> SUBMITTED -> CANCELLED
    status: TaskDraftStatus = TaskDraftStatus.FILLING

    # 核心槽位存储：Key为槽位名
    slots: Dict[str, SlotValueDTO] = Field(default_factory=dict)
    
    missing_slots: List[str] = []   # 必填但缺失的
    invalid_slots: List[str] = []   # 格式错误的

    # 调度信息（用于定时/循环任务）
    schedule: Optional[ScheduleDTO] = None

    # 任务控制元数据
    is_cancelable: bool = True  # 是否允许取消（默认 true）
    is_resumable: bool = True  # 是否支持暂停/恢复

    original_utterances: List[str] = [] # 这一轮填槽过程中的用户历史输入
    created_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    updated_at: float = Field(default_factory=lambda: datetime.now().timestamp())
    
    # 新增：是否是动态/开放任务，决定是否走硬编码的必填项检查
    is_dynamic_schema: bool = True
    
    # 新增：LLM认为还需要澄清的问题
    next_clarification_question: Optional[str] = None
    
    # 新增：LLM对当前任务完整度的信心 (0.0 - 1.0)
    completeness_score: float = 0.0