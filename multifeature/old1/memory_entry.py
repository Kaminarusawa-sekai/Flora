from datetime import datetime

# =================== 记忆条目类 ===================
class MemoryEntry:
    def __init__(self, entry_type: str, content: dict):
        self.type = entry_type
        self.content = content
        self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {
            "type": self.type,
            "content": self.content,
            "timestamp": self.timestamp
        }

    @staticmethod
    def from_dict(data):
        return MemoryEntry(
            entry_type=data["type"],
            content=data["content"]
        )

    def __repr__(self):
        return f"[{self.type}] {self.content.get('summary', '')}"