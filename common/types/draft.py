from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

class AgentState(str, Enum):
    IDLE = "idle"
    COLLECTING_PARAMS = "collecting_params"
    DRAFT_SAVED = "draft_saved"

class TaskDraft:
    """DTO for task draft"""
    def __init__(
        self,
        id: str,
        action_type: str,
        collected_params: Dict[str, Any],
        missing_params: List[str],
        last_question: str,
        created_at: datetime,
        updated_at: datetime
    ):
        self.id = id
        self.action_type = action_type
        self.collected_params = collected_params
        self.missing_params = missing_params
        self.last_question = last_question
        self.created_at = created_at
        self.updated_at = updated_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "collected_params": self.collected_params,
            "missing_params": self.missing_params,
            "last_question": self.last_question,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskDraft":
        return cls(
            id=data["id"],
            action_type=data["action_type"],
            collected_params=data["collected_params"],
            missing_params=data["missing_params"],
            last_question=data["last_question"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
