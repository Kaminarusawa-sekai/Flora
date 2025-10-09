# memory/short_term.py
from typing import List, Dict

class ShortTermMemory:
    def __init__(self, max_history: int = 10):
        self.max_history = max_history
        self.history: List[Dict[str, str]] = []

    def add_message(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def get_history(self, n: int = None) -> List[Dict[str, str]]:
        n = n or self.max_history
        return self.history[-n:]

    def format_history(self, n: int = 6) -> str:
        recent = self.get_history(n)
        return "\n".join([f"{m['role']}: {m['content']}" for m in recent])

    def clear(self):
        self.history.clear()