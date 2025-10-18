from dashscope import Generation
from typing import Dict, Any,List,Optional, Union
import json
import json5 as jsonlib  # 使用 json5 作为解析器

class QwenLLM():
    def __init__(self, model_name: str = "qwen-max", vl_model_name:str="qwen-vl-max",api_key: str = None):
        if api_key:
            import dashscope
            dashscope.api_key = api_key
        self.model_name = model_name
        self.vl_model_name = vl_model_name


    def generate(
        self,
        prompt: str,
        images: List[str] = None,
        parse_json: bool = False,
        json_schema: Dict[str, Any] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """
        统一的文本/多模态生成接口。根据是否提供图片自动选择调用模式。

        :param prompt: 提示词
        :param images: 可选，图像 URL 或 base64 列表。如果提供，则使用多模态模型
        :param parse_json: 是否尝试从输出中提取并解析 JSON
        :param json_schema: 可选，用于提示性校验 JSON 字段（不强制）
        :param max_retries: 最大重试次数
        :param **kwargs: 透传给底层模型的参数（如 temperature, top_p 等）
        :return: 字符串 或 解析后的 dict，失败返回 None
        """
        # 默认空列表处理
        images = images or []

        # 选择模型：有图用 VL，无图用文本模型
        if images:
            # 使用多模态模型 (VL)
            return self._call_vl_model(
                prompt=prompt,
                images=images,
                parse_json=parse_json,
                json_schema=json_schema,
                max_retries=max_retries,
                **kwargs
            )
        else:
            # 使用纯文本模型
            return self._call_text_model(
                prompt=prompt,
                parse_json=parse_json,
                json_schema=json_schema,
                max_retries=max_retries,
                **kwargs
            )

    def _call_text_model(
        self,
        prompt: str,
        parse_json: bool = False,
        json_schema: Dict[str, Any] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """调用纯文本模型"""
        for _ in range(max_retries):
            try:
                response = Generation.call(
                    model=self.model_name,
                    prompt=str(prompt),
                    **kwargs
                )
                if not response or not response.output or not response.output.text:
                    continue

                text = response.output.text.strip()
                print(f"QwenLLM: {text}")

                if not parse_json:
                    return text

                # 尝试提取 JSON
                json_str = self._extract_json(text)  # 假设你已有此方法
                if not json_str:
                    print(f"[QwenCaller] 未找到 JSON: {text[:200]}...")
                    continue

                result = json.loads(json_str)

                # 提示性字段检查
                if json_schema:
                    missing = [k for k in json_schema.keys() if k not in result]
                    if missing:
                        print(f"[QwenCaller] JSON 缺少字段 {missing}，期望: {list(json_schema.keys())}")

                return result

            except Exception as e:
                print(f"[QwenCaller Text Call Error] {e}")
                continue

        return None


    def _call_vl_model(
        self,
        prompt: str,
        images: List[str],
        parse_json: bool = False,
        json_schema: Dict[str, Any] = None,
        max_retries: int = 3,
        **kwargs
    ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
        """调用多模态模型"""
        for _ in range(max_retries):
            try:
                response = Generation.call(
                    model=self.vl_model_name,
                    prompt=prompt,
                    images=images,
                    **kwargs
                )
                if not response:
                    continue

                text = str(response.strip())
                if not parse_json:
                    return text

                # 尝试提取 JSON
                json_str = self._extract_json(text)
                if not json_str:
                    print(f"[QwenCaller] 未找到 JSON: {text[:200]}...")
                    continue

                result = json.loads(json_str)

                # 提示性字段检查
                if json_schema:
                    missing = [k for k in json_schema.keys() if k not in result]
                    if missing:
                        print(f"[QwenCaller] JSON 缺少字段 {missing}，期望: {list(json_schema.keys())}")

                return result

            except Exception as e:
                print(f"[QwenCaller VL Call Error] {e}")
                continue

        return None
        
    def multi_generate(self, prompt: str, context: List[Dict[str, str]], max_tokens: int = 1000) -> str:
        from dashscope import Generation

        # 将 context 转换为 Qwen 所需格式：将 role 改为 user/assistant
        formatted_messages = []
        for msg in context:
            role = 'user' if msg['role'] == 'user' else 'assistant'
            formatted_messages.append({'role': role, 'content': msg['content']})
        formatted_messages.append({'role': 'user', 'content': prompt})

        response = Generation.call(
            model=self.model_name,
            input={'prompt': prompt, 'history': [(msg['role'], msg['content']) for msg in context]}
        )

        return response.output.text
    
    # def generate_vlu(
    #     self,
    #     prompt: str,
    #     images: List[str],
    #     parse_json: bool = False,
    #     json_schema: Dict[str, Any] = None,  # 可选：用于校验结构
    #     max_retries: int = 3,
    #     **kwargs
    # ) -> Union[Optional[str], Optional[Dict[str, Any]]]:
    #     """
    #     通用多模态调用接口

    #     :param prompt: 提示词（由调用方构造）
    #     :param images: 图像 URL 或 base64 列表
    #     :param parse_json: 是否尝试解析 JSON 输出
    #     :param json_schema: 可选，用于校验字段（仅提示，不强制）
    #     :param max_retries: 重试次数
    #     :param **kwargs: 透传给底层模型（如 temperature, top_p 等）
    #     :return: 字符串 或 解析后的 dict，失败返回 None
    #     """
    #     for _ in range(max_retries):
    #         try:
    #             # 调用多模态模型
    #             response = self.vl.generate(
    #                 prompt=prompt,
    #                 images=images,  # 假设模型接口支持 images 参数
    #                 **kwargs
    #             )
    #             if not response:
    #                 continue

    #             text = str(response.strip())
    #             if not parse_json:
    #                 return text

    #             # 尝试提取 JSON
    #             json_str = self._extract_json(text)
    #             if not json_str:
    #                 print(f"[QwenCaller] 未找到 JSON: {text[:200]}...")
    #                 continue

    #             result = json.loads(json_str)

    #             # 可选：简单校验关键字段（仅提示，不抛异常）
    #             if json_schema:
    #                 missing = [k for k in json_schema.keys() if k not in result]
    #                 if missing:
    #                     print(f"[QwenCaller] JSON 缺少字段 {missing}，期望: {list(json_schema.keys())}")

    #             return result

    #         except Exception as e:
    #             print(f"[QwenCaller VL Call Error] {e}")
    #             continue

    #     return None

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """
        从文本中提取第一个最外层的合法 JSON 对象或数组。
        使用 json5 支持宽松语法（单引号、注释、尾逗号、无引号键等）。
        能跳过非法或不完整的结构，继续搜索后续可能的 JSON。
        """
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
                    start = i  # 记录最外层开始位置
                stack.append(c)

            elif c in '}]':
                if stack:
                    opening = stack.pop()
                    # 检查括号匹配
                    if (opening == '{' and c != '}') or (opening == '[' and c != ']'):
                        # 不匹配，清空状态，继续
                        stack.clear()
                        start = -1
                    else:
                        if not stack and start != -1:
                            # 最外层闭合，尝试解析
                            candidate = text[start:i+1]
                            try:
                                jsonlib.loads(candidate)  # 使用 json5 解析
                                return candidate
                            except Exception:
                                # 解析失败，重置 start，继续寻找下一个
                                start = -1
                # else: 多余的 ] 或 }，忽略
            i += 1

        return None
