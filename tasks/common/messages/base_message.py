from datetime import datetime
from uuid import uuid4
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from thespian.actors import ActorAddress

from common.context.context_entry import ContextEntry
class BaseMessage(BaseModel):
    message_type: str
    source: str = Field(default="")
    destination: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.now)
    id: str = Field(default_factory=lambda: str(uuid4()))

    model_config = ConfigDict(
        json_encoders={datetime: lambda v: v.isoformat()}
    )

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



