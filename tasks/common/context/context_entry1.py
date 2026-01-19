from pydantic import BaseModel, Field, ConfigDict
from typing import Any, Optional, List
import time


class SemanticPointer(BaseModel):
    """
    语义指针：自包含的参数语义描述。

    用于消解代词歧义，将模糊的参数描述转化为精确的语义实体。
    例如：将 "该用户的ID" 转化为 "昨天第二个需要退款资格检查的客户的ID"
    """
    model_config = ConfigDict(extra='allow')

    param_name: str                          # 参数名，如 "client_id"
    original_desc: str                       # 原始描述，如 "该用户的ID"
    resolved_desc: str                       # 补全后的描述
    confidence: float = 1.0                  # 置信度 (0-1)
    resolution_chain: List[str] = Field(default_factory=list)  # 解析链，记录每级补全的信息
    source_agent_path: List[str] = Field(default_factory=list) # 信息来源的 Agent 路径
    has_ambiguity: bool = False              # 是否包含模糊引用


class ContextEntry(BaseModel):
    value: Any
    source: str                 # 来源：如 "user_input", "agent_step_2", "tool_output_profile"
    task_path: str              # 产生该值的任务路径（用于追踪）
    timestamp: float = Field(default_factory=time.time)
    confidence: float = 1.0     # 可选：置信度（用于冲突消解）
    semantic_pointer: Optional[SemanticPointer] = None  # 语义指针（用于代词消歧）