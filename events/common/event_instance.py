from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .enums import ActorType, ScheduleType, EventInstanceStatus


class EventInstance(BaseModel):
    id: str
    trace_id: str
    parent_id: Optional[str] = None
    job_id: str
    def_id: str  # 关联任务定义

    # 【关键优化】物化路径，格式如 "/root_id/parent_id/"
    # 作用：一个 SQL 就能查出整棵子树，不用递归查询
    node_path: str
    depth: int = 0

    actor_type: ActorType
    role: Optional[str] = None
    layer: int = 0
    is_leaf_agent: bool = False

    schedule_type: ScheduleType = ScheduleType.ONCE
    round_index: Optional[int] = None
    cron_trigger_time: Optional[datetime] = None

    status: EventInstanceStatus
    
    # 进度条 (0-100)
    progress: int = 0
    
    # 【控制信号】
    # 指令塔写入 "PAUSE", Agent 读取并执行
    control_signal: Optional[str] = None
    
    depends_on: Optional[List[str]] = None
    split_count: int = 0
    completed_children: int = 0

    # 上下文数据引用 (不直接存大字段，存 OSS/S3 key 或 redis key)
    input_ref: Optional[str] = None
    output_ref: Optional[str] = None
    
    # 原有字段
    input_params: Dict[str, Any] = Field(default_factory=dict)
    error_msg: Optional[str] = None

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))