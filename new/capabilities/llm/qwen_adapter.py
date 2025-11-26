"""Qwen LLM适配器（基于 DashScope SDK）"""
from typing import Dict, Any, List, Optional, Union
import json
from ..capability_base import CapabilityBase


class QwenAdapter(CapabilityBase):
    """
    基于 DashScope SDK 的 Qwen 适配器
    支持文本生成、多模态（VL）、JSON 解析、对话历史等
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "qwen-max",
        vl_model_name: str = "qwen-vl-max"
    ):
        super().__init__()
        
        # 尝试从 config 获取 API Key（如果未传入）
        if not api_key:
            try:
                from config import DASHSCOPE_API_KEY
                api_key = DASHSCOPE_API_KEY
            except ImportError:
                pass

        if not api_key:
            raise ValueError("DashScope API key is required. Provide via 'api_key' or config.DASHSCOPE_API_KEY")

        # 初始化 DashScope SDK
        import dashscope
        dashscope.api_key = api_key

        self.model_name = model_name
        self.vl_model_name = vl_model_name
        self.dashscope = dashscope

    def get_capability_type(self) -> str:
        return 'llm'

    def generate(
        self,
        prompt: str,
        images: Optional[List[str]] = None,
        parse_json: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Union[str, Dict[str, Any], None]:
        """
        统一生成接口：自动根据是否含图片选择文本或 VL 模型
        """
        images = images or []
        if images:
            return self._call_vl_model(prompt, images, parse_json, json_schema, max_retries, **kwargs)
        else:
            return self._call_text_model(prompt, parse_json, json_schema, max_retries, **kwargs)

    def _call_text_model(
        self,
        prompt: str,
        parse_json: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Union[str, Dict[str, Any], None]:
        for _ in range(max_retries):
            try:
                response = self.dashscope.Generation.call(
                    model=self.model_name,
                    prompt=prompt,
                    **kwargs
                )
                if not response or not hasattr(response, 'output') or not response.output.text:
                    continue

                text = response.output.text.strip()
                if not parse_json:
                    return text

                json_str = self._extract_json(text)
                if not json_str:
                    continue

                result = json.loads(json_str)
                if json_schema:
                    missing = [k for k in json_schema if k not in result]
                    if missing:
                        print(f"[QwenAdapter] JSON 缺少字段: {missing}")
                return result

            except Exception as e:
                print(f"[QwenAdapter Text Error] {e}")
                continue
        return None

    def _call_vl_model(
        self,
        prompt: str,
        images: List[str],
        parse_json: bool = False,
        json_schema: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Union[str, Dict[str, Any], None]:
        for _ in range(max_retries):
            try:
                response = self.dashscope.MultiModalConversation.call(
                    model=self.vl_model_name,
                    messages=[{
                        "role": "user",
                        "content": [
                            {"image": img} for img in images
                        ] + [{"text": prompt}]
                    }],
                    **kwargs
                )

                if not response or not response.output or not response.output.choices:
                    continue

                text = response.output.choices[0].message.content[0].text.strip()
                if not parse_json:
                    return text

                json_str = self._extract_json(text)
                if not json_str:
                    continue

                result = json.loads(json_str)
                if json_schema:
                    missing = [k for k in json_schema if k not in result]
                    if missing:
                        print(f"[QwenAdapter] JSON 缺少字段: {missing}")
                return result

            except Exception as e:
                print(f"[QwenAdapter VL Error] {e}")
                continue
        return None

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> Dict[str, Any]:
        """
        支持多轮对话（仅文本，不支持 VL）
        messages 格式: [{"role": "user", "content": "..."}, ...]
        """
        try:
            # DashScope 文本模型支持 messages 格式（需 qwen-turbo/max/plus 等）
            response = self.dashscope.Generation.call(
                model=self.model_name,
                messages=messages,
                **kwargs
            )

            if response and response.output and response.output.text:
                return {
                    "content": response.output.text.strip(),
                    "model": self.model_name,
                    "usage": getattr(response, 'usage', {}),
                    "id": getattr(response, 'request_id', '')
                }
            else:
                return {"content": "Error: No response", "error": "Empty response"}

        except Exception as e:
            return {"content": f"Error: {str(e)}", "error": str(e)}

    def embedding(self, texts: List[str], model: str = "text-embedding-v1") -> List[List[float]]:
        try:
            response = self.dashscope.TextEmbedding.call(
                model=model,
                input=texts
            )
            if response and response.output and response.output.embeddings:
                return [item.embedding for item in response.output.embeddings]
            else:
                return [[] for _ in texts]
        except Exception as e:
            print(f"[QwenAdapter Embedding Error] {e}")
            return [[] for _ in texts]

    def set_api_key(self, api_key: str) -> None:
        self.dashscope.api_key = api_key

    def set_default_model(self, model: str) -> None:
        self.model_name = model

    def get_supported_models(self) -> List[str]:
        return [
            "qwen-max", "qwen-plus", "qwen-turbo", "qwen-max-longcontext",
            "qwen-vl-max", "qwen-vl-plus"
        ]

    def batch_generate(self, prompts: List[str], **kwargs) -> List[str]:
        # 简单串行实现（DashScope SDK 本身不提供 batch 接口）
        return [self.generate(prompt, **kwargs) for prompt in prompts]

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """从文本中提取第一个合法 JSON 对象或数组"""
        if not text or not isinstance(text, str):
            return None

        stack = []
        start = -1
        i = 0
        n = len(text)

        while i < n:
            c = text[i]
            if c in '{[':
                if not stack:
                    start = i
                stack.append(c)
            elif c in '}]':
                if stack:
                    opening = stack.pop()
                    if (opening == '{' and c != '}') or (opening == '[' and c != ']'):
                        stack.clear()
                        start = -1
                    elif not stack and start != -1:
                        candidate = text[start:i+1]
                        try:
                            json.loads(candidate)
                            return candidate
                        except Exception:
                            start = -1
            i += 1
        return None