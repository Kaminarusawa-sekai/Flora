"""LLM适配模块"""

from .interface import ILLMCapability
from .qwen_llm import QwenLLM

__all__ = ['ILLMCapability', 'QwenLLM']
