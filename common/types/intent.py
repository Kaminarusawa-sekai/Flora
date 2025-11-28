from typing import Dict, Any, Optional
from enum import Enum

class IntentType(str, Enum):
    TASK = "task"
    QUERY = "query"
    SYSTEM = "system"
    REFLECTION = "reflection"
    CHAT = "chat"
    AMBIGUOUS = "ambiguous"
    CONTINUE_DRAFT = "continue_draft"

class IntentResult:
    """DTO for intent recognition results"""
    def __init__(
        self,
        intent: IntentType,
        confidence: float,
        reason: str,
        raw_input: Optional[str] = None,
        method: Optional[str] = None
    ):
        self.intent = intent
        self.confidence = confidence
        self.reason = reason
        self.raw_input = raw_input
        self.method = method
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "raw_input": self.raw_input,
            "method": self.method
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IntentResult":
        return cls(
            intent=IntentType(data["intent"]),
            confidence=data["confidence"],
            reason=data["reason"],
            raw_input=data.get("raw_input"),
            method=data.get("method")
        )
