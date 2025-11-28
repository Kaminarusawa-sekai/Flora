from typing import Dict, Any, Optional
from capabilities.capability_base import CapabilityBase
from capabilities.registry import CapabilityRegistry
from common.types.intent import IntentResult, IntentType

class IIntentRouterCapability(CapabilityBase):
    """Interface for intent classification capability"""
    def classify_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        """Classify user input intent"""
        raise NotImplementedError

class IntentRouterCapability(IIntentRouterCapability):
    """Intent classification capability using LLM"""
    def __init__(self):
        super().__init__()
        self.llm = None
    
    def initialize(self, config: Dict[str, Any] = None):
        """Initialize the capability"""
        from capabilities.llm.qwen_adapter import QwenAdapter
        self.llm = QwenAdapter()
        self.llm.initialize(config.get("llm", {}) if config else {})
    
    def shutdown(self):
        """Shutdown the capability"""
        pass
    
    def get_capability_type(self) -> str:
        """Return capability type"""
        return "cognition"
    
    def _build_system_prompt(self) -> str:
        """Build system prompt for intent classification"""
        intent_types = IntentType
        intent_descriptions = "\n".join([f'- "{k.value}": {self._get_intent_description(k)}' for k in intent_types])
        return f"""你是一个智能任务助理的意图识别模块。请严格根据用户输入，判断其主意图类别。

可用意图类别如下：
{intent_descriptions}

要求：
1. 只输出一个 JSON 对象，不要任何其他文字。
2. JSON 必须包含字段：intent（字符串）、confidence（0.0~1.0 的浮点数）、reason（简短中文解释）。
3. intent 必须是上述类别之一。
4. confidence 表示你对该判断的确信程度。
5. 如果用户输入模糊、缺少上下文或难以判断，请返回 intent: "ambiguous"。
6. 如果用户希望继续之前未完成的任务草稿，请返回 intent: "continue_draft"。

示例输出：
{{"intent": "task", "confidence": 0.95, "reason": "用户明确要求添加一个新任务"}}
"""
    
    def _get_intent_description(self, intent_type: IntentType) -> str:
        """Get description for intent type"""
        descriptions = {
            IntentType.TASK: "用户希望创建、修改、完成、评论或管理某个具体任务",
            IntentType.QUERY: "用户希望查询任务状态、历史记录、统计数据等信息",
            IntentType.SYSTEM: "用户希望操作系统设置、导出数据、账户管理等系统功能",
            IntentType.REFLECTION: "用户希望对自身行为、任务完成情况做复盘、总结或分析",
            IntentType.CHAT: "用户进行问候、表达情绪、闲聊等非功能性对话",
            IntentType.AMBIGUOUS: "输入信息不足、模糊不清，无法可靠判断意图",
            IntentType.CONTINUE_DRAFT: "用户希望继续之前未完成的任务草稿"
        }
        return descriptions[intent_type]
    
    def classify_intent(self, user_input: str, context: Optional[Dict[str, Any]] = None) -> IntentResult:
        """Classify user input intent"""
        system_prompt = self._build_system_prompt()
        
        try:
            # 使用QwenAdapter调用大模型
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input.strip()}
            ]
            
            response = self.llm.generate_chat(messages, temperature=0.1, max_tokens=200)
            
            if "error" in response:
                return IntentResult(
                    intent=IntentType.AMBIGUOUS,
                    confidence=0.0,
                    reason=f"系统异常: {response['error']}",
                    raw_input=user_input,
                    method="error"
                )
            
            raw_output = response.get("content", "").strip()
            
            # 尝试提取 JSON（兼容可能的 markdown code block）
            if raw_output.startswith("```json"):
                raw_output = raw_output[7:-3].strip()
            elif raw_output.startswith("```"):
                raw_output = raw_output[3:-3].strip()
            
            import json
            result_dict = json.loads(raw_output)
            
            # 校验字段
            if "intent" not in result_dict or result_dict["intent"] not in [t.value for t in IntentType]:
                raise ValueError("Invalid intent")
            if "confidence" not in result_dict:
                result_dict["confidence"] = 0.5
            if "reason" not in result_dict:
                result_dict["reason"] = "LLM未提供理由"
            
            result_dict["raw_input"] = user_input
            result_dict["method"] = "qwen"
            
            return IntentResult.from_dict(result_dict)
            
        except Exception as e:
            return IntentResult(
                intent=IntentType.AMBIGUOUS,
                confidence=0.0,
                reason=f"系统异常: {str(e)}",
                raw_input=user_input,
                method="error"
            )

# Register the capability
from capabilities.registry import capability_registry
capability_registry.register_class("intent_router", IntentRouterCapability)
