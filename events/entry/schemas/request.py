from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class StartTraceRequest(BaseModel):
    root_def_id: str = Field(..., description="根节点定义ID")
    trace_id: str = Field(..., description="跟踪ID，由外部传入")
    input_params: Dict[str, Any] = Field(default_factory=dict, description="启动参数")

class SubTaskMeta(BaseModel):
    id: str = Field(..., description="子任务ID，由外部传入")
    def_id: str
    name: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)

class SplitTaskRequest(BaseModel):
    parent_id: str = Field(..., description="父事件ID")
    subtasks_meta: List[SubTaskMeta] = Field(..., description="子任务元数据")

class ControlNodeRequest(BaseModel):
    signal: str = Field(..., pattern="^(CANCEL|PAUSE|RESUME)$", description="控制信号")
