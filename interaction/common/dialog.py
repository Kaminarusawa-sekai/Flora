from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class DialogTurn(BaseModel):
    role: str
    utterance: str
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp())
    enhanced_utterance: Optional[str] = None
    session_id: str  # 新增：关联到具体会话
    user_id: str  # 新增：关联到具体用户

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "utterance": self.utterance,
            "timestamp": self.timestamp,
            "enhanced_utterance": self.enhanced_utterance,
            "session_id": self.session_id,
            "user_id": self.user_id
        }