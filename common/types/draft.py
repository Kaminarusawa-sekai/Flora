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
        updated_at: datetime,
        session_id: Optional[str] = None,
        status: str = "editing"
    ):
        self.id = id
        self.action_type = action_type
        self.collected_params = collected_params
        self.missing_params = missing_params
        self.last_question = last_question
        self.created_at = created_at
        self.updated_at = updated_at
        self.session_id = session_id
        self.status = status
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "collected_params": self.collected_params,
            "missing_params": self.missing_params,
            "last_question": self.last_question,
            "session_id": self.session_id,
            "status": self.status,
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
            session_id=data.get("session_id"),
            status=data.get("status", "editing"),
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"])
        )
    
    def to_task_spec_dict(self) -> Dict[str, Any]:
        """转换为TaskSpec字典格式"""
        return {
            "task_type": self.action_type,
            "params": self.collected_params,
            "requires_confirmation": True,
            "metadata": {
                "source": "dialog",
                "created_by": "user"
            }
        }
