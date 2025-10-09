# utils/qwen_client.py
import os
import json
from dashscope import Generation
from http import HTTPStatus

# 请设置你的阿里云 DashScope API Key
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY")
if not DASHSCOPE_API_KEY:
    raise ValueError("请设置环境变量 DASHSCOPE_API_KEY")

def call_qwen(messages: list, response_format: str = "text") -> dict:
    """
    调用 Qwen 模型
    :param messages: 对话历史，格式为 [{"role": "user", "content": "..."}, ...]
    :param response_format: 返回格式，"text" 或 "json_object"
    :return: {"status": "success", "content": "..."} 或 {"status": "error", "message": "..."}
    """
    try:
        response = Generation.call(
            model="qwen-plus",  # 或 qwen-turbo, qwen-max
            messages=messages,
            result_format='message',
            output_json_format=response_format == "json_object"
        )
        if response.status_code == HTTPStatus.OK:
            content = response.output.choices[0]['message']['content']
            if response_format == "json_object":
                content = json.loads(content)
            return {"status": "success", "content": content}
        else:
            return {
                "status": "error",
                "message": f"Request failed: {response.message}"
            }
    except Exception as e:
        return {"status": "error", "message": str(e)}



