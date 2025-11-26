import json
import dashscope
from dashscope import Generation
from typing import Dict, Any, Optional

# 设置你的 API Key（建议用环境变量）
# export DASHSCOPE_API_KEY='your-key'
dashscope.api_key = 'YOUR_API_KEY_HERE'  # 或从 os.getenv 读取

# 意图定义
INTENT_TYPES = {
    "task": "用户希望创建、修改、完成、评论或管理某个具体任务",
    "query": "用户希望查询任务状态、历史记录、统计数据等信息",
    "system": "用户希望操作系统设置、导出数据、账户管理等系统功能",
    "reflection": "用户希望对自身行为、任务完成情况做复盘、总结或分析",
    "chat": "用户进行问候、表达情绪、闲聊等非功能性对话",
    "ambiguous": "输入信息不足、模糊不清，无法可靠判断意图",
    "continue_draft": "用户希望继续之前未完成的任务草稿"
}

def build_system_prompt() -> str:
    intent_descriptions = "\n".join([f'- "{k}": {v}' for k, v in INTENT_TYPES.items()])
    return f"""你是一个智能任务助理的意图识别模块。请严格根据用户输入，判断其主意图类别。

可用意图类别如下：
{intent_descriptions}

要求：
1. 只输出一个 JSON 对象，不要任何其他文字。
2. JSON 必须包含字段：intent（字符串）、confidence（0.0~1.0 的浮点数）、reason（简短中文解释）。
3. intent 必须是上述6个值之一。
4. confidence 表示你对该判断的确信程度。
5. 如果用户输入模糊、缺少上下文或难以判断，请返回 intent: "ambiguous"。

示例输出：
{{"intent": "task", "confidence": 0.95, "reason": "用户明确要求添加一个新任务"}}
"""

def classify_intent_with_qwen(user_input: str, model: str = "qwen-max") -> Optional[Dict[str, Any]]:
    system_prompt = build_system_prompt()
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input.strip()}
    ]
    
    try:
        response = Generation.call(
            model=model,
            messages=messages,
            result_format="message",
            temperature=0.1,  # 降低随机性，提高稳定性
            max_tokens=200
        )
        
        if response.status_code != 200:
            print(f"Qwen API error: {response.code} - {response.message}")
            return None
        
        raw_output = response.output.choices[0].message.content.strip()
        
        # 尝试提取 JSON（兼容可能的 markdown code block）
        if raw_output.startswith("```json"):
            raw_output = raw_output[7:-3].strip()
        elif raw_output.startswith("```"):
            raw_output = raw_output[3:-3].strip()
        
        try:
            result = json.loads(raw_output)
            # 校验字段
            if "intent" not in result or result["intent"] not in INTENT_TYPES:
                raise ValueError("Invalid intent")
            if "confidence" not in result:
                result["confidence"] = 0.5
            if "reason" not in result:
                result["reason"] = "LLM未提供理由"
            result["raw_input"] = user_input
            result["method"] = "qwen"
            return result
        except json.JSONDecodeError as e:
            print(f"JSON parse failed: {e}. Raw output: {raw_output}")
            return {
                "intent": "ambiguous",
                "confidence": 0.3,
                "reason": "LLM返回非JSON格式",
                "raw_input": user_input,
                "method": "qwen_fallback"
            }
            
    except Exception as e:
        print(f"Unexpected error: {e}")
        return {
            "intent": "ambiguous",
            "confidence": 0.0,
            "reason": "系统异常",
            "raw_input": user_input,
            "method": "error"
        }

def should_clarify(intent_result: dict, confidence_threshold: float = 0.7) -> bool:
    """
    判断是否需要澄清
    """
    if intent_result["intent"] == "ambiguous":
        return True
    if intent_result.get("confidence", 0) < confidence_threshold:
        return True
    return False


# ===== 使用示例 =====
if __name__ == "__main__":
    test_inputs = [
        "加个任务：明天开会前准备PPT",
        "我今天完成了几个任务？",
        "你好呀！",
        "导出我所有的任务数据",
        "这周我效率怎么样？",
        "那个东西弄一下",
        "把周报任务分配给小李"  # 即使含协作词，仍属 task
    ]
    
    for inp in test_inputs:
        result = classify_intent_with_qwen(inp)
        print(f"输入: {inp}")
        print(f"输出: {json.dumps(result, ensure_ascii=False, indent=2)}\n")