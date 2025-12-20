from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .enums import ActorType, ScheduleType, NodeType


class TaskDefinition(BaseModel):
    id: str = Field(..., description="任务定义唯一ID")
    name: str
    
    # 核心字段：决定了前端怎么渲染，以及后端怎么处理超时/重试
    node_type: NodeType
    
    # 原有字段
    actor_type: ActorType
    role: Optional[str] = None
    code_ref: str = Field(..., description="如 docker://my/agent:v1")
    entrypoint: str = "main.run"

    schedule_type: ScheduleType = ScheduleType.ONCE
    cron_expr: Optional[str] = None
    loop_config: Optional[Dict[str, Any]] = None

    resource_profile: str = "default"
    strategy_tags: List[str] = Field(default_factory=list)

    default_params: Dict[str, Any] = Field(default_factory=dict)
    
    # 策略配置
    default_timeout: int = 3600
    retry_policy: Dict[str, Any] = Field(default_factory=lambda: {"max_retries": 3, "backoff": "exponential"})
    
    # UI 配置：决定在拓扑图上的颜色、图标
    ui_config: Dict[str, Any] = Field(default_factory=lambda: {"icon": "robot", "color": "#FF0000"})
    
    is_active: bool = True
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))