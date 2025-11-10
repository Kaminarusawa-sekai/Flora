# llm_orchestrator.py
import json
import asyncio
from openai import AsyncOpenAI
import os
from config import SYSTEM_ROLE, VECTOR_DIM

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))


##TODO: 维度需要适配数量，而非固定维度
class LLMOrchestrator:
    def __init__(self, user_goal: str):
        self.user_goal = user_goal
        self.optimization_schema = None  # {"dimensions": [...], "initial_vector": [...]}
        self.history = []

    async def discover_schema(self) -> dict:
        """Step 1: 让 LLM 自行决定优化哪些维度"""
        prompt = f"""
用户目标：{self.user_goal}

请分析该任务，确定一组最关键的可调参数（称为“优化维度”），用于指导后续实验。
每个维度应有名称和简要说明。

此外，请建议一个初始隐向量（长度为 {VECTOR_DIM}，值在 -1 到 1 之间），作为起点。

输出格式（严格 JSON）：
{{
  "dimensions": [
    {{"name": "temperature", "description": "控制生成随机性"}},
    {{"name": "prompt_style", "description": "提示词风格"}}
  ],
  "initial_vector": [0.1, -0.3, ..., 0.0]
}}
"""
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        self.optimization_schema = json.loads(resp.choices[0].message.content)
        return self.optimization_schema

    async def vector_to_instruction(self, vector: list, context: dict = None) -> str:
        """Step 2: 隐向量 → 自然语言指令"""
        history_snippet = ""
        if self.history:
            last = self.history[-1]
            history_snippet = f"上一轮指令: {last['instruction']}\n结果摘要: {last['output'][:200]}..."

        prompt = f"""
用户目标：{self.user_goal}
{history_snippet}

当前隐向量（长度 {len(vector)}）：
{vector}

请将此向量解释为一组具体的调整策略，并生成一条清晰、可执行的自然语言指令。
指令应直接告诉执行者“做什么”，无需解释向量含义。

示例输出：
“使用更正式的语气，提高创造性，减少示例数量，重点强调可靠性。”
"""
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": prompt}
            ]
        )
        return resp.choices[0].message.content.strip()

    async def output_to_score(self, raw_output: str) -> dict:
        """Step 3: 原始输出 → 分数 + 结构化反馈"""
        prompt = f"""
用户目标：{self.user_goal}

原始输出：
{raw_output[:1000]}

请评估此输出在多大程度上达成了用户目标，给出 0.0 ~ 1.0 的分数。
同时，用一句话总结主要优点或不足。

输出格式（严格 JSON）：
{{
  "score": 0.75,
  "feedback": "创意不错，但未突出核心卖点"
}}
"""
        resp = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": SYSTEM_ROLE},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"}
        )
        result = json.loads(resp.choices[0].message.content)
        self.history.append({
            "instruction": "...",  # will be filled by caller
            "output": raw_output,
            "score": result["score"],
            "feedback": result["feedback"]
        })
        return result