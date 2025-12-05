from typing import Dict, Any, Optional
from capabilities.capability_base import CapabilityBase
from common.types.intent import IntentResult


class IIntentRouterCapability(CapabilityBase):
    """Interface for intent classification capability"""
    def classify_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        """Classify user input intent"""
        raise NotImplementedError
