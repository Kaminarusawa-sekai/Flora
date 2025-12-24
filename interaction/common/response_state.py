from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime, timezone
from .base import ActionType, TaskStatusSummary, TaskSummary
from .task_draft import TaskDraftDTO

class SuggestedActionDTO(BaseModel):
    type: ActionType
    title: str
    payload: str  # 点击后回传给后端的指令，如 "CONFIRM_Draft_123"

class SystemResponseDTO(BaseModel):
    """🖥️ [6. SystemResponseDTO] 返回给前端的响应"""
    session_id: str
    response_text: str
    
    # 交互增强
    suggested_actions: List[SuggestedActionDTO] = []
    
    # 状态透传
    task_status: Optional[TaskStatusSummary] = None
    
    # 控制前端行为
    requires_input: bool = False   # 是否弹起键盘/输入框
    awaiting_slot: Optional[str] = None # 正在问哪个槽
    
    # 结构化数据展示 (卡片、表格等)
    display_data: Optional[Dict[str, Any]] = None

class DialogStateDTO(BaseModel):
    """💬 [5. DialogStateDTO] 全局会话状态"""
    session_id: str
    user_id: str  # 新增：关联到具体用户
    current_intent: Optional[str] = None
    
    # 指针
    active_task_draft: Optional[TaskDraftDTO] = None      # 正在填槽的
    active_task_execution: Optional[str] = None           # 正在跑的TaskID
    
    # 任务栈 (处理中断/话题转移)
    pending_tasks: List[str] = [] # 存 DraftID 或 TaskID
    
    # --- 上下文记忆 (用于指代消解) ---
    # 如用户说 "把刚才那个任务删了"，从这里找 "刚才那个"
    recent_tasks: List[TaskSummary] = []
    last_mentioned_task_id: Optional[str] = None

    is_in_idle_mode: bool = False # 闲聊模式
    
    # --- 新增字段：意图处理与澄清 ---
    requires_clarification: bool = False
    clarification_context: Optional[Dict[str, Any]] = None
    clarification_message: Optional[str] = None
    missing_required_slots: List[str] = Field(default_factory=list)
    

    # ✅ 【新增】待确认状态锁
    # 当这个为 True 时，系统的第一优先级是判断用户是否确认
    waiting_for_confirmation: bool = False 
    confirmation_action: Optional[str] = None  # 等待确认的动作类型
    # (可选) 存一下到底在确认什么，防止上下文丢失
    confirmation_payload: Optional[Dict[str, Any]] = None

    # --- 新增字段：会话生命周期 ---
    last_updated: datetime =  Field(default_factory=lambda: datetime.now(timezone.utc))

    