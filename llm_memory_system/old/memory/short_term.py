# memory/short_term.py
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import List, Dict, Any
import copy

@dataclass
class Message:
    role: str
    content: str
    timestamp: str = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

class ShortTermMemory:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.history: List[Message] = []
        self.working_state: Dict[str, Any] = {}
        self.focus_context: str = ""
        self.last_active: datetime = datetime.now()

    def add_message(self, role: str, content: str, metadata: Dict = None):
        self.history.append(Message(role, content, metadata=metadata))
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history:]
        self.last_active = datetime.now()

    def get_history(self, n: int = None) -> List[Dict]:
        hist = self.history[-n:] if n else self.history
        return [asdict(m) for m in hist]

    def set_state(self, key: str, value: Any):
        self.working_state[key] = value
        self.last_active = datetime.now()

    def get_state(self, key: str, default=None):
        return self.working_state.get(key, default)

    def update_focus(self, content: str):
        self.focus_context = content
        self.last_active = datetime.now()

    def get_focus(self) -> str:
        return self.focus_context

    def is_expired(self, timeout_minutes: int = 30) -> bool:
        return datetime.now() - self.last_active > timedelta(minutes=timeout_minutes)

    def snapshot(self) -> Dict:
        return {
            "history": [asdict(m) for m in self.history],
            "working_state": copy.deepcopy(self.working_state),
            "focus_context": self.focus_context,
            "last_active": self.last_active.isoformat()
        }

    def restore_from_snapshot(self, snap: Dict):
        self.history = [Message(**m) for m in snap["history"]]
        self.working_state = snap["working_state"]
        self.focus_context = snap["focus_context"]
        self.last_active = datetime.fromisoformat(snap["last_active"])

    def reset(self):
        self.history.clear()
        self.working_state.clear()
        self.focus_context = ""
        self.last_active = datetime.now()



