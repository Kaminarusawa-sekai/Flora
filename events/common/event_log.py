from datetime import datetime, timezone
from typing import Optional, Dict
from pydantic import BaseModel, Field


class EventLog(BaseModel):
    """
    直接对应执行系统的 Args，用于记录流水账
    """
    id: str = Field(..., description="日志唯一ID")
    instance_id: str  # 关联 EventInstance.id
    trace_id: str
    
    event_type: str  # 对应 Args.event_type，建议使用枚举如 STARTED, RUNNING, PAUSED, COMPLETED, FAILED
    level: str = "INFO"  # INFO, WARN, ERROR
    
    content: Optional[str] = None  # 对应 Args.data 的简要描述或日志文本
    payload_snapshot: Optional[Dict] = None  # 对应 Args.enriched_context_snapshot (按需采样)
    
    # 建议新增：执行节点信息，方便运维排查
    execution_node: Optional[str] = None  # 执行机器的 IP 或 Pod Name
    agent_id: Optional[str] = None  # 执行代理 ID
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
