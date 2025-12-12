from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime
import uuid

@dataclass
class TaskDraft:
    id: str
    user_id: str
    intent_type: str          # 用户想干什么 (e.g., "query_sales")
    collected_params: Dict    # 已收集的参数 (e.g., {"region": "north"})
    missing_params: List[str] # 缺少的参数 (e.g., ["date"])
    status: str               # "COLLECTING", "READY", "ABORTED"
    last_question: Optional[str] = None            # 上次问的问题
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()
    
    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "intent_type": self.intent_type,
            "collected_params": self.collected_params,
            "missing_params": self.missing_params,
            "status": self.status,
            "last_question": self.last_question,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }