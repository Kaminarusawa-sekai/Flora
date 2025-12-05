"""LLM维度解析能力组件"""
import json
import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from ..capability_base import CapabilityBase
from .interface import IDimensionParserCapability


class DimensionParserCapability(IDimensionParserCapability):
    """
    LLM维度解析能力，负责:
    1. 自动发现优化维度
    2. 将隐向量转换为自然语言指令
    3. 评估执行输出并打分
    """
    
    def __init__(self, user_goal: str, vector_dim: int = 5):
        """
        初始化维度解析能力
        
        Args:
            user_goal: 用户目标
            vector_dim: 隐向量维度
        """
        super().__init__()
        self.user_goal = user_goal
        self.vector_dim = vector_dim
        self.optimization_schema = None  # {"dimensions": [...], "initial_vector": [...]}  # noqa: E501
        self.history = []
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    def get_capability_type(self) -> str:
        """获取能力类型"""
        return "llm_dimension_parser"
    
    def discover_schema(self) -> Dict[str, Any]:
        """
        步骤1: 让LLM自行决定优化哪些维度
        
        Returns:
            dict: 包含维度信息和初始向量的字典
        """
        system_role = os.getenv("SYSTEM_ROLE", "你是一个专业的优化专家，负责分析任务并生成优化方案")  # noqa: E501
        
        prompt = f"""
用户目标：{self.user_goal}

请分析该任务，确定一组最关键的可调参数（称为“优化维度”），用于指导后续实验。
每个维度应有名称和简要说明。

此外，请建议一个初始隐向量（长度为 {self.vector_dim}，值在 -1 到 1 之间），作为起点。

输出格式（严格 JSON）：
{{
  "dimensions": [
    {{"name": "temperature", "description": "控制生成随机性"}},
    {{"name": "prompt_style", "description": "提示词风格"}}
  ],
  "initial_vector": [0.1, -0.3, ..., 0.0]
}}
"""
        
        resp = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            response_format={{"type": "json_object"}}
        )
        
        self.optimization_schema = json.loads(resp.choices[0].message.content)
        return self.optimization_schema
    
    def vector_to_instruction(self, vector: List[float], context: Optional[Dict[str, Any]] = None) -> str:
        """
        步骤2: 隐向量 → 自然语言指令
        
        Args:
            vector: 隐向量
            context: 上下文信息（可选）
            
        Returns:
            str: 自然语言指令
        """
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
        
        system_role = os.getenv("SYSTEM_ROLE", "你是一个专业的优化专家，负责分析任务并生成优化方案")  # noqa: E501
        
        resp = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ]
        )
        
        return resp.choices[0].message.content.strip()
    
    def output_to_score(self, raw_output: str) -> Dict[str, Any]:
        """
        步骤3: 原始输出 → 分数 + 结构化反馈
        
        Args:
            raw_output: 执行输出内容
            
        Returns:
            Dict[str, Any]: 包含评分和反馈的字典
        """
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
        
        system_role = os.getenv("SYSTEM_ROLE", "你是一个专业的优化专家，负责分析任务并生成优化方案")  # noqa: E501
        
        resp = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_role},
                {"role": "user", "content": prompt}
            ],
            response_format={{"type": "json_object"}}
        )
        
        result = json.loads(resp.choices[0].message.content)
        
        # 保存历史记录
        self.history.append({
            "instruction": getattr(self, '_last_instruction', '未记录'),
            "output": raw_output,
            "score": result["score"],
            "feedback": result["feedback"]
        })
        
        return result
    
    def set_last_instruction(self, instruction: str) -> None:
        """
        设置上一次的指令，用于历史记录
        
        Args:
            instruction: 上一次的指令
        """
        self._last_instruction = instruction
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        获取历史记录
        
        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        return self.history
