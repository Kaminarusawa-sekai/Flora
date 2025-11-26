from dataclasses import dataclass
from typing import Dict, Optional, List
from datetime import datetime
import uuid

@dataclass
class TaskDraft:
    id: str
    action_type: str              # e.g., "create_task", "schedule_meeting"
    collected_params: Dict        # 已收集的参数
    missing_params: List[str]     # 还缺哪些字段
    last_question: str            # 上次问的问题
    created_at: datetime
    updated_at: datetime
    
    def to_dict(self):
        return {
            "id": self.id,
            "action_type": self.action_type,
            "collected_params": self.collected_params,
            "missing_params": self.missing_params,
            "last_question": self.last_question,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }