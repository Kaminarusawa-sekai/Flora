from pydantic import BaseModel, Field, ConfigDict
from typing import Any
import time

class ContextEntry(BaseModel):
    value: Any
    source: str                 # 来源：如 "user_input", "agent_step_2", "tool_output_profile"
    task_path: str              # 产生该值的任务路径（用于追踪）
    timestamp: float = Field(default_factory=time.time)
    confidence: float = 1.0     # 可选：置信度（用于冲突消解）