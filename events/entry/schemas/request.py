from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum

# #TODO：移到common，定义信号枚举，方便文档展示
class ControlSignalEnum(str, Enum):
    CANCEL = "CANCEL"
    PAUSE = "PAUSE"
    RESUME = "RESUME"

# ==========================================
# 1. 启动链路请求
# ==========================================
class StartTraceRequest(BaseModel):
    """
    启动一个新的 Trace
    """
    request_id: str = Field(..., description="全局请求ID (Request ID)，用于关联 trace_id")
    trace_id: str = Field(..., description="链路ID (Trace ID)，由外部生成并传入")

    input_params: Dict[str, Any] = Field(default_factory=dict, description="初始输入参数")
    
    # 可选字段
    user_id: Optional[str] = Field(None, description="操作用户ID")

# ==========================================
# 2. 拓扑分裂/扩展请求
# ==========================================
class SubTaskMeta(BaseModel):
    id: str = Field(..., description="子任务ID (Instance ID)，由外部预生成")
    def_id: Optional[str] = Field(None, description="任务定义ID (可选)")
    name: Optional[str] = Field(None, description="任务名称")
    params: Dict[str, Any] = Field(default_factory=dict, description="子任务输入参数")
    actor_type: str = Field("AGENT", description="执行角色类型: AGENT/HUMAN/SYSTEM")
    role: Optional[str] = Field(None, description="角色名称")
    # 允许接收其他动态字段，方便未来扩展
    extra: Dict[str, Any] = Field(default_factory=dict)

class SplitTaskRequest(BaseModel):
    """
    动态生成子任务 (DAG 扩展)
    """
    parent_id: str = Field(..., description="父节点ID")
    subtasks_meta: List[SubTaskMeta] = Field(..., description="子任务元数据列表")
    
    # 记录决策依据
    reasoning_snapshot: Optional[Dict[str, Any]] = Field(None, description="分裂任务的思维链/原因快照")

# ==========================================
# 3. 核心：通用事件上报 (Sync Execution)
# ==========================================
class ExecutionEventRequest(BaseModel):
    """
    执行系统上报的状态变更事件
    """
    task_id: str = Field(..., description="当前执行的任务/实例ID")
    trace_id: str = Field(..., description="所属链路ID (用于校验)")
    event_type: str = Field(..., description="事件类型: STARTED, RUNNING, COMPLETED, FAILED, PROGRESS")
    
    # 执行数据
    data: Optional[Any] = Field(None, description="输出数据 或 进度数据")
    error: Optional[str] = Field(None, description="错误信息")
    
    # 上下文快照 (这是 Agent 系统的核心，用于状态恢复)
    enriched_context_snapshot: Optional[Dict[str, Any]] = Field(None, description="执行时的上下文快照")
    
    # 元数据
    agent_id: Optional[str] = Field(None, description="执行该任务的 Agent ID")
    worker_id: Optional[str] = Field(None, description="物理执行单元 ID (Pod ID / Thread ID)")
    
    # 额外信息
    realtime_info: Optional[Dict[str, Any]] = Field(None, description="实时信息，如当前的 step")

# ==========================================
# 4. 控制信号请求
# ==========================================
class ControlNodeRequest(BaseModel):
    signal: ControlSignalEnum = Field(..., description="控制信号")
