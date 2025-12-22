from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

# --- 新增：对应执行系统的 Args ---
class ExecutionEventRequest(BaseModel):
    """
    通用事件上报请求，完全对应执行系统的 Args
    """
    task_id: str = Field(..., description="任务/实例ID")
    event_type: str = Field(..., description="事件类型: STARTED, RUNNING, COMPLETED, FAILED, PROGRESS")
    trace_id: str
    
    # 上下文与数据
    data: Optional[Any] = None  # 结果数据或进度数据
    error: Optional[str] = None # 错误信息
    enriched_context_snapshot: Optional[Dict[str, Any]] = Field(None, description="关键上下文快照")
    
    # 元数据
    source: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: Optional[float] = None

# --- 修改：增强启动请求 ---
class StartTraceRequest(BaseModel):
    root_def_id: str = Field(..., description="根节点定义ID")
    trace_id: str = Field(..., description="跟踪ID，由外部传入")
    input_params: Dict[str, Any] = Field(default_factory=dict, description="启动参数")
    
    # 新增：允许传入用户ID，用于审计
    user_id: Optional[str] = None
    # 新增：允许传入初始上下文（比如用户的问题原文）
    initial_context: Optional[Dict[str, Any]] = None

class SubTaskMeta(BaseModel):
    id: str = Field(..., description="子任务ID，由外部传入")
    def_id: str
    name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

# --- 修改：增强分裂请求 ---
class SplitTaskRequest(BaseModel):
    parent_id: str = Field(..., description="父事件ID")
    subtasks_meta: List[SubTaskMeta] = Field(..., description="子任务元数据")
    
    # 新增：记录 Agent 为什么要分裂的“思维链”快照
    reasoning_snapshot: Optional[Dict[str, Any]] = None

class ControlNodeRequest(BaseModel):
    signal: str = Field(..., pattern="^(CANCEL|PAUSE|RESUME)$", description="控制信号")
