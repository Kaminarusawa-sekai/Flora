from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field
from typing import Optional

class BaseMessage(BaseModel):
    message_type: str
    # source: str
    # destination: str
    timestamp: datetime = Field(default_factory=datetime.now)
    id: str = Field(default_factory=lambda: str(uuid4()))

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}

    def to_json(self) -> str:
        from ..utils import to_json
        return to_json(self.model_dump(mode='json'))

    @classmethod
    def from_json(cls, json_str: str):
        from ..utils import from_json
        data = from_json(json_str)
        return cls.model_validate(data)

    def __str__(self) -> str:
        return f"{self.__class__.__name__}[{self.id}] {self.message_type} from {self.source} to {self.destination} at {self.timestamp}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.id}, type={self.message_type}, source={self.source}, dest={self.destination}, ts={self.timestamp})"


class TaskMessage(BaseMessage):
    task_id: str
    trace_id: str  # ← 新增：根请求 ID，用于全链路追踪
    task_path: str  # ← 新增：如 "/0/2/1"，表示在 整个迭代树中，当前任务在第几层，第几步，第几个子任务 中的位置


