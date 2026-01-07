from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .enums import ActorType,EventInstanceStatus


class EventInstance(BaseModel):
    id: str
    task_id: str
    trace_id: str
    request_id: Optional[str] = None  # 关联请求ID，用于支持 request_id -> trace_id 的一对多关系
    parent_id: Optional[str] = None
    def_id: Optional[str] = None  # 关联任务定义，变为可选
    user_id: str
    worker_id: Optional[str] = None  # 新增：标识当前处理该实例的worker
    name: Optional[str] = None  # 新增：事件实例名称

    # 【关键优化】物化路径，格式如 "/root_id/parent_id/"
    # 作用：一个 SQL 就能查出整棵子树，不用递归查询
    node_path: str
    depth: int = 0

    actor_type: ActorType # 改为字符串类型
    role: Optional[str] = None
    layer: int = 0
    is_leaf_agent: bool = False

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
    
    # 建议修改：错误详情，支持存储更丰富的错误信息
    error_detail: Optional[Dict[str, Any]] = None
    
    # 建议新增：运行时快照，用于存储执行系统上报的最新关键上下文
    runtime_state_snapshot: Optional[Dict[str, Any]] = None
    
    # 建议新增：结果摘要，用于存储简短的返回值
    result_summary: Optional[str] = None
    
    # 建议新增：交互信号，Agent -> 指令塔，比如 "NEED_HUMAN_CONFIRM"
    interactive_signal: Optional[str] = None

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))