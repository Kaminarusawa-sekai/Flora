from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DialogTurn(BaseModel):
    role: str
    utterance: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    enhanced_utterance: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "utterance": self.utterance,
            "timestamp": self.timestamp,
            "enhanced_utterance": self.enhanced_utterance
        }