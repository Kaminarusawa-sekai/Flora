# qwen_client.py
import dashscope
from http import HTTPStatus
import json
from config import DASHSCOPE_API_KEY

dashscope.api_key = DASHSCOPE_API_KEY

def call_qwen(prompt: str) -> str:
    response = dashscope.Generation.call(
        model='qwen-max',
        messages=[{'role': 'user', 'content': prompt}],
        result_format='message',
        temperature=0.1,
        top_p=0.5,
        enable_json_output=False
    )
    if response.status_code == HTTPStatus.OK:
        return response.output.choices[0].message.content
    else:
        return ""

def call_qwen_json(prompt: str) -> dict:
    response = dashscope.Generation.call(
        model='qwen-max',
        messages=[{'role': 'user', 'content': prompt}],
        result_format='message',
        temperature=0.1,
        top_p=0.5,
        enable_json_output=True
    )
    if response.status_code == HTTPStatus.OK:
        try:
            return json.loads(response.output.choices[0].message.content)
        except:
            return {}
    else:
        return {}