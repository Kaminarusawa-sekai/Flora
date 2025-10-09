# policy_engine.py
from models import OptimizationAction
from qwen_client import call_qwen_json

# 你自己的逻辑引擎接口（示例）
class YourLogicEngine:
    def deduce(self, state: dict) -> dict:
        # 你可以在这里调用你已实现的逻辑引擎
        return {
            "action_type": "prompt_refinement",
            "params": {"clarity": "high"},
            "confidence": 0.9,
            "reason": "用户反馈图表不清晰"
        }

class PolicyEngine:
    def __init__(self):
        self.logic_engine = YourLogicEngine()

    def select_action(self, state: dict) -> OptimizationAction:
        raw_action = self.logic_engine.deduce(state)
        action = OptimizationAction(**raw_action)

        # Qwen 验证动作
        validate_prompt = f"""
        请评估以下优化建议是否合理：
        当前问题：{state.get('context_summary', '')}
        建议动作：{action.action_type} 参数：{action.params}
        理由：{action.reason}
        返回 JSON：
        {{ "valid": true, "confidence": 0.9, "suggestion": "补充建议" }}
        """
        qwen_feedback = call_qwen_json(validate_prompt)
        action.valid_by_qwen = qwen_feedback.get("valid", False)
        action.qwen_suggestion = qwen_feedback.get("suggestion", "")
        return action