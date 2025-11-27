# models/task_node.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel
import uuid

class TaskNodeType(str, Enum):
    CREATED = "created"       # 初始创建
    MODIFIED = "modified"     # 用户修改参数/时间等
    EXECUTED = "executed"     # 执行了一次（含结果）
    COMMENTED = "commented"   # 用户追加评论
    CORRECTED = "corrected"   # 用户修正结果
    BRANCHED = "branched"     # 主动分叉（如“试试新方案”）

class TaskNode(BaseModel):
    id: str  # 全局唯一 node ID
    task_root_id: str  # 同一棵树的所有节点共享此 ID（用于聚合）
    parent_id: Optional[str] = None  # 父节点（None 表示根）
    
    user_id: str
    type: TaskNodeType
    timestamp: datetime
    
    # 快照：该节点的状态
    goal: str
    description: str  # 用户原始输入或操作描述
    status: str  # pending/completed...
    schedule_config: Optional[Dict] = None
    subtasks: List[Dict] = []
    execution_result: Optional[str] = None
    comment: Optional[str] = None
    corrected_result: Optional[str] = None
    
    # 元数据：供 LLM 检索和理解
    summary_for_llm: str  # 自动生成的简洁摘要（关键！）
    memory_ids: List[str] = []  # 关联的记忆片段 ID（写入 Mem0 后回填）