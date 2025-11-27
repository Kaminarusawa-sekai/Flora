# messages.py

from dataclasses import dataclass
from typing import Optional, Dict, Any
from datetime import datetime, timezone

@dataclass
class TaskEvent:
    event_type: str  # "started", "finished", "failed", "subtask_spawned"
    task_id: str
    agent_id: str
    timestamp: datetime
    details: Dict[str, Any]

    def __init__(self, event_type: str, task_id: str, agent_id: str, details: Optional[Dict] = None):
        self.event_type = event_type
        self.task_id = task_id
        self.agent_id = agent_id
        self.timestamp = datetime.now(timezone.utc)
        self.details = details or {}