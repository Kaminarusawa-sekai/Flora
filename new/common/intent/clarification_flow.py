import json
import dashscope
from dashscope import Generation
from typing import List, Dict, Optional, Tuple

# 假设你已有 classify_intent_with_qwen 函数（来自上一节）
from intent_router import classify_intent_with_qwen, INTENT_TYPES

dashscope.api_key = 'YOUR_API_KEY_HERE'  # 或从环境变量读取

# 意图中文名映射（用于用户友好显示）
INTENT_DISPLAY_NAMES = {
    "task": "创建或管理任务",
    "query": "查询任务信息",
    "system": "系统设置或操作",
    "reflection": "复盘或总结",
    "chat": "闲聊"
}

def generate_clarification_options(user_input: str, top_k: int = 3) -> List[Dict[str, str]]:
    """
    使用 Qwen 动态生成最可能的意图选项（排除 ambiguous）
    """
    valid_intents = {k: v for k, v in INTENT_TYPES.items() if k != "ambiguous"}
    descriptions = "\n".join([f'- "{k}": {v}' for k, v in valid_intents.items()])
    
    prompt = f"""用户输入了一句话，但意图不明确。请从以下意图类别中，选出最可能的 {top_k} 个选项（按可能性排序），并为每个选项生成一句自然的用户可能想表达的话。

可用意图：
{descriptions}

要求：
1. 只输出 JSON 数组，不要任何其他文字。
2. 每个元素包含：intent（意图ID）、example（示例句子）、reason（简短理由）。
3. example 必须是用户可能说的原话风格，不要太正式。
4. 不要包含 "ambiguous"。

用户输入："{user_input}"

示例输出：
[{{"intent": "task", "example": "加个任务：买牛奶", "reason": "可能是想新建任务"}}, ...]
"""
    
    try:
        response = Generation.call(
            model="qwen-plus",  # 用 plus 平衡速度与质量
            prompt=prompt,
            temperature=0.3,
            max_tokens=300
        )
        
        if response.status_code != 200:
            raise Exception(f"API error: {response.code}")
        
        raw = response.output.text.strip()
        if raw.startswith("```json"):
            raw = raw[7:-3].strip()
        elif raw.startswith("```"):
            raw = raw[3:-3].strip()
        
        options = json.loads(raw)
        # 过滤非法 intent
        filtered = [
            opt for opt in options[:top_k]
            if opt.get("intent") in valid_intents
        ]
        return filtered[:top_k] if filtered else _fallback_clarification_options(user_input)
        
    except Exception as e:
        print(f"Qwen clarification generation failed: {e}")
        return _fallback_clarification_options(user_input)


def _fallback_clarification_options(user_input: str) -> List[Dict[str, str]]:
    """
    规则兜底：基于关键词猜测
    """
    lower = user_input.lower()
    candidates = []
    
    if any(kw in lower for kw in ["做", "加", "安排", "任务", "记得"]):
        candidates.append({"intent": "task", "example": f"加个任务：{user_input}", "reason": "可能想创建任务"})
    if any(kw in lower for kw in ["查", "看", "有吗", "多少", "完成"]):
        candidates.append({"intent": "query", "example": f"我完成了哪些任务？", "reason": "可能想查询任务"})
    if any(kw in lower for kw in ["设置", "导出", "清空", "退出"]):
        candidates.append({"intent": "system", "example": "导出我的任务数据", "reason": "可能想操作系统"})
    if any(kw in lower for kw in ["总结", "复盘", "效率", "周报"]):
        candidates.append({"intent": "reflection", "example": "帮我总结本周工作", "reason": "可能想复盘"})
    if len(candidates) == 0:
        # 默认给两个高频选项
        candidates = [
            {"intent": "task", "example": f"创建任务：{user_input}", "reason": "可能想记录待办"},
            {"intent": "query", "example": f"查询：{user_input}", "reason": "可能想了解信息"}
        ]
    
    return candidates[:3]


def format_clarification_message(options: List[Dict[str, str]]) -> str:
    """
    生成用户友好的澄清消息
    """
    parts = ["我不太确定你的意思，你是想：\n"]
    for i, opt in enumerate(options, 1):
        display = INTENT_DISPLAY_NAMES.get(opt["intent"], opt["intent"])
        parts.append(f"{i}. {display}？比如：“{opt['example']}”")
    parts.append("\n请输入选项编号（1/2/3）或直接重述你的需求。")
    return "\n".join(parts)


def handle_user_clarification_choice(choice_input: str, options: List[Dict[str, str]]) -> Optional[Dict]:
    """
    处理用户对澄清选项的选择
    返回新的 intent_result 结构
    """
    choice_input = choice_input.strip()
    
    # 情况1：用户输入数字
    if choice_input.isdigit():
        idx = int(choice_input) - 1
        if 0 <= idx < len(options):
            selected = options[idx]
            # 模拟用户说了 example 中的内容
            simulated_input = selected["example"]
            return classify_intent_with_qwen(simulated_input)
    
    # 情况2：用户重述了新句子 → 直接重新分类
    return classify_intent_with_qwen(choice_input)


# ===== 使用示例：完整澄清流程 =====
def safe_process_user_input(user_input: str) -> Dict:
    """
    安全处理用户输入：自动触发澄清并闭环
    """
    intent_result = classify_intent_with_qwen(user_input)
    
    # 第一次判断是否需要澄清
    if not should_clarify(intent_result):
        return intent_result
    
    # 生成澄清选项
    options = generate_clarification_options(user_input)
    clarification_msg = format_clarification_message(options)
    print("[Assistant]", clarification_msg)
    
    # 模拟用户回复（实际中应等待真实输入）
    user_response = input("[User] ")  # 在真实系统中替换为异步等待
    
    # 处理用户澄清回复
    clarified_result = handle_user_clarification_choice(user_response, options)
    
    # 再次检查是否仍模糊（防止用户又输模糊内容）
    if should_clarify(clarified_result, confidence_threshold=0.6):
        # 可选：最多澄清2轮，否则放弃
        print("[Assistant] 抱歉，我还是不太明白。你可以试试说：“帮我加个任务：XXX” 或 “查一下我今天的任务”")
        return {"intent": "chat", "confidence": 0.9, "reason": "多次澄清失败", "raw_input": user_input, "method": "final_fallback"}
    
    return clarified_result


def should_clarify(intent_result: dict, confidence_threshold: float = 0.7) -> bool:
    if intent_result["intent"] == "ambiguous":
        return True
    if intent_result.get("confidence", 0) < confidence_threshold:
        return True
    return False


# ===== 测试 =====
if __name__ == "__main__":
    test_input = "那个东西弄一下"
    print(f"原始输入: {test_input}")
    final_intent = safe_process_user_input(test_input)
    print("\n最终意图:", json.dumps(final_intent, ensure_ascii=False, indent=2))