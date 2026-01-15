"""Qwen LLM适配器（基于 DashScope SDK）"""
from typing import Dict, Any, List, Optional, Union
import json5 as json
from .interface import ILLMCapability
import logging
logger = logging.getLogger(__name__)

class QwenLLM(ILLMCapability):
    """
    基于 DashScope SDK 的 Qwen 适配器
    支持文本生成、多模态（VL）、JSON 解析、对话历史等
    """

    def __init__(
        self,

    ):
        
        super().__init__(

        )
        self.model_name = None
        self.vl_model_name = None
        self.dashscope = None
        self.is_initialized = False

    def initialize(self, config: Dict[str, Any]) -> None:
        logger.info("开始初始化Qwen LLM适配器")
        # 从配置中获取参数（如果提供）
        api_key = None
        if 'api_key' in config:
            api_key = config['api_key'] 
        else:
            # 尝试从 config 获取 API Key（如果未传入）
           
            try:
                from config import DASHSCOPE_API_KEY
                api_key = DASHSCOPE_API_KEY
            except ImportError:
                pass

            if not api_key:
                raise ValueError("DashScope API key is required. Provide via 'api_key' or config.DASHSCOPE_API_KEY")

            # 初始化 DashScope SDK
        import dashscope
        logger.info("DashScope API key has been set")
        dashscope.api_key = api_key
        self.dashscope = dashscope
        if 'model_name' in config:
            self.model_name = config['model_name'] or self.model_name
        else:
            self.model_name="qwen-max"
        if 'vl_model_name' in config:
            self.vl_model_name = config['vl_model_name'] or self.vl_model_name
        else:
            self.vl_model_name="qwen-vl-max"
        logger.info(f"Qwen LLM适配器初始化完成，model_name={self.model_name}, vl_model_name={self.vl_model_name}")
        self.is_initialized = True

    def shutdown(self) -> None:
        logger.info("开始关闭Qwen LLM适配器")
        # 清理资源
        self.is_initialized = False
        logger.info("Qwen LLM适配器已关闭")

    def get_capability_type(self) -> str:
        return 'qwen_llm'

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
        logger.info(f"开始生成，parse_json={parse_json}, max_retries={max_retries}, images_count={len(images) if images else 0}")
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
        logger.info(f"调用文本模型，model={self.model_name}, parse_json={parse_json}")
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
                logger.info(f"[QwenLLM Text Response] {text}")
                if not parse_json:
                    return text

                json_str = self._extract_json(text)
                if not json_str:
                    continue

                result = json.loads(json_str)
                if json_schema:
                    missing = [k for k in json_schema if k not in result]
                    if missing:
                        logger.warning(f"JSON 缺少字段: {missing}")
                logger.info(f"文本模型调用成功，返回JSON格式结果")
                return result

            except Exception as e:
                logger.exception("Text model error")
                continue
        logger.error(f"文本模型调用失败，已尝试{max_retries}次")
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
        logger.info(f"调用VL模型，model={self.vl_model_name}, parse_json={parse_json}, images_count={len(images)}")
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
                        logger.warning(f"JSON 缺少字段: {missing}")
                logger.info(f"VL模型调用成功，返回JSON格式结果")
                return result

            except Exception as e:
                logger.exception("VL model error")
                continue
        logger.error(f"VL模型调用失败，已尝试{max_retries}次")
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
        logger.info(f"开始对话生成，messages_count={len(messages)}")
        try:
            # DashScope 文本模型支持 messages 格式（需 qwen-turbo/max/plus 等）
            response = self.dashscope.Generation.call(
                model=self.model_name,
                messages=messages,
                **kwargs
            )
            logger.debug(f"DashScope response: {response}")
            if response and response.output and response.output.text:
                result = {
                    "content": response.output.text.strip(),
                    "model": self.model_name,
                    "usage": getattr(response, 'usage', {}),
                    "id": getattr(response, 'request_id', '')
                }
                logger.info(f"对话生成成功，返回结果长度={len(result['content'])}字符")
                return result
            else:
                logger.error("DashScope返回空响应")
                return {"content": "Error: No response", "error": "Empty response"}

        except Exception as e:
            logger.exception("对话生成失败")
            return {"content": f"Error: {str(e)}", "error": str(e)}

    def embedding(self, text: str, model: str = "text-embedding-v1") -> List[float]:
        logger.info(f"开始嵌入生成，model={model}")
        try:
            response = self.dashscope.TextEmbedding.call(
                model=model,
                input=[text]
            )
            if response and response.output and response.output.embeddings:
                embedding = response.output.embeddings[0].embedding
                logger.info(f"嵌入生成成功，嵌入长度={len(embedding)}")
                return embedding
            else:
                logger.error("嵌入生成失败，返回空结果")
                return []
        except Exception as e:
            logger.exception("Embedding error")
            return []

    def set_api_key(self, api_key: str) -> None:
        logger.info("更新API key")
        self.dashscope.api_key = api_key

    def set_default_model(self, model: str) -> None:
        logger.info(f"更新默认模型，model={model}")
        self.model_name = model

    def get_supported_models(self) -> List[str]:
        return [
            "qwen-max", "qwen-plus", "qwen-turbo", "qwen-max-longcontext",
            "qwen-vl-max", "qwen-vl-plus"
        ]

    def batch_generate(self, prompts: List[str], **kwargs) -> List[str]:
        logger.info(f"开始批量生成，prompts_count={len(prompts)}")
        # 简单串行实现（DashScope SDK 本身不提供 batch 接口）
        return [self.generate(prompt, **kwargs) for prompt in prompts]

    def extract_json_from_response(self, response_text: str, multiple: bool = False) -> Union[Optional[str], List[str]]:
        """
        从大模型返回的文本中提取JSON格式内容
        
        Args:
            response_text: 大模型返回的文本
            multiple: 是否提取所有JSON对象/数组，默认为False（仅提取第一个）
            
        Returns:
            若multiple=False，返回第一个合法JSON字符串或None；
            若multiple=True，返回所有合法JSON字符串的列表
        """
        logger.info(f"开始从响应中提取JSON，multiple={multiple}")
        if not response_text or not isinstance(response_text, str):
            return [] if multiple else None
            
        if multiple:
            return self._extract_multiple_json(response_text)
        else:
            return self._extract_json(response_text)
    
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
    
    @staticmethod
    def _extract_multiple_json(text: str) -> List[str]:
        """从文本中提取所有合法 JSON 对象或数组"""
        if not text or not isinstance(text, str):
            return []

        json_list = []
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
                            json_list.append(candidate)
                            start = -1  # 重置，寻找下一个JSON
                        except Exception:
                            start = -1
            i += 1
        return json_list