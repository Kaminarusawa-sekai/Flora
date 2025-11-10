# === 纯粹的LLM评估器（不维护历史）===
from typing import Any, Optional
from llm import QwenLLM
from agent.optimization.optimization_adapter import EvaluatorAdapter


# === 纯粹的LLM评估器（不维护历史）===
class LLMEvaluator(EvaluatorAdapter):
    """
    纯粹的基于大模型的评估器
    不维护历史记录，只负责根据当前和历史结果计算分数
    """
    def __init__(self, llm_client=None):
        llm=QwenLLM()
        self.llm_client = llm_client or llm

    def evaluate(self, task_id: str, current_result: Any, previous_result: Optional[Any] = None) -> float:
        """
        评估函数：分析当前结果与命令的匹配度 + 与上次结果的差异
        """
        # 解析当前结果
        if isinstance(current_result, dict):
            command = current_result.get('command', '')
            current_output = current_result.get('result', str(current_result))
        else:
            command = getattr(current_result, 'command', '')
            current_output = str(current_result)

        # 解析上次结果
        prev_output = None
        if previous_result:
            if isinstance(previous_result, dict):
                prev_output = previous_result.get('result', str(previous_result))
            else:
                prev_output = str(previous_result)

        # 1. 评估命令与当前结果的匹配程度
        match_score = self._evaluate_command_match(command, current_output)

        # 2. 比较与上次结果的差异
        diff_score = 0.0
        diff_direction = "neutral"
        if prev_output:
            diff_score, diff_direction = self._compare_with_previous(
                command, prev_output, current_output
            )

        # 3. 综合评估
        overall_score = self._synthesize_evaluation(
            match_score, diff_score, diff_direction
        )

        return overall_score

    def _evaluate_command_match(self, command: str, result: str) -> float:
        """评估命令与执行结果的匹配程度"""
        prompt = f"""
        请评估以下语言命令与其执行结果的匹配程度：
        
        命令：{command}
        执行结果：{result}
        
        请以JSON格式返回：
        {{
            "match_score": 0.0-1.0之间的匹配分数,
            "reason": "简要说明匹配程度的原因"
        }}
        """
        
        try:
            response = self.llm_client.generate(prompt)
            data = response
            return max(0.0, min(1.0, data.get('match_score', 0.5)))
        except:
            return 0.5  # 默认分数

    def _compare_with_previous(self, command: str, prev_result: str, current_result: str) -> tuple:
        """比较当前结果与上次结果的差异"""
        prompt = f"""
        请比较两次执行相同语言命令的结果差异：
        
        命令：{command}
        上次结果：{prev_result}
        当前结果：{current_result}
        
        请以JSON格式返回：
        {{
            "diff_direction": "improvement|degradation|neutral|unknown",
            "diff_score": -1.0到1.0之间的差异分数，正数表示改进，负数表示退化,
            "description": "差异的详细描述"
        }}
        """
        
        try:
            data = self.llm_client.generate(prompt)

            direction = data.get('diff_direction', 'neutral')
            score = max(-1.0, min(1.0, data.get('diff_score', 0.0)))
            return score, direction
        except:
            return 0.0, 'neutral'

    def _synthesize_evaluation(self, match_score: float, diff_score: float, diff_direction: str) -> float:
        """综合评估匹配度和差异度"""
        prompt = f"""
        请综合评估以下指标：
        - 命令与结果匹配度：{match_score:.2f}
        - 与上次结果差异：{diff_score:.2f} ({diff_direction})
        
        请以JSON格式返回综合评估：
        {{
            "overall_score": 0.0-1.0之间的综合分数,
            "improvement_direction": "positive|negative|neutral",
            "confidence": 0.0-1.0之间的置信度
        }}
        """
        
        try:
            response = self.llm_client.generate(prompt)
            data = response
            return max(0.0, min(1.0, data.get('overall_score', 0.5)))
        except:
            # 基于简单规则的回退
            base_score = match_score
            if diff_direction == 'improvement':
                base_score = min(1.0, base_score + abs(diff_score) * 0.1)
            elif diff_direction == 'degradation':
                base_score = max(0.0, base_score - abs(diff_score) * 0.1)
            return max(0.0, min(1.0, base_score))
