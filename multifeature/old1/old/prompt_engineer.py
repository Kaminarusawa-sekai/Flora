# prompt_engineer.py

from qwen_adapter import call_qwen

class BehaviorFeatureExtractor:
    def __init__(self):
        pass

    def extract_from_behavior(self, behavior_text: str, previous_features: list = None):
        """
        给定用户的行为描述和已有特征，返回新的特征列表
        """

        prev_feat_str = ", ".join(previous_features) if previous_features else "无"

        prompt = f"""
你是一个性格特征分析专家。请根据用户的以下行为描述，结合其已有特征，推测可能具备的新特征。

【已有特征】：
{prev_feat_str}

【当前行为描述】：
"{behavior_text}"

【分析要求】：
1. 不依赖用户直接表达的内容，而是从行为中推断。
2. 提取符合以下标准的特征：
   - 可观察性：能通过行为、选择、互动方式等观察到。
   - 稳定性：不是短暂状态，而是倾向模式。
   - 区分性：有助于区分个体差异。
   - 描述性：避免评价性词汇，尽量客观。
   - 心理意义：对行为、思维、人际有影响。

【输出格式】：
每行一个特征，英文命名，括号内中文解释，例如：
analytical_thinker (偏好逻辑分析和深度思考)
"""

        raw_response = call_qwen(prompt)
        if not raw_response:
            return []

        features = [f.strip() for f in raw_response.splitlines() if f.strip()]
        return features