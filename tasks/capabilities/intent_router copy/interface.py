from typing import Dict, Any, Optional
from ..capability_base import CapabilityBase

# 本地定义 IntentResult 类，避免依赖缺失
class IntentResult:
    """Intent result class"""
    def __init__(self, intent_type: str, confidence: float, parameters: Dict[str, Any]):
        self.intent_type = intent_type
        self.confidence = confidence
        self.parameters = parameters

class IIntentRouterCapability(CapabilityBase):
    """Interface for intent classification capability"""
    def classify_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        """Classify user input intent"""
        raise NotImplementedError
