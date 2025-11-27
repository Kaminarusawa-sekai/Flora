import json
from typing import Dict, Any, Optional
from datetime import datetime
import uuid

# 导入Qwen适配器
from capabilities.llm.qwen_adapter import QwenAdapter

# 导入Draft相关类
from common.draft.conversation_manager import ConversationManager, AgentState
from common.draft.task_draft import TaskDraft

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
3. intent 必须是上述类别之一。
4. confidence 表示你对该判断的确信程度。
5. 如果用户输入模糊、缺少上下文或难以判断，请返回 intent: "ambiguous"。
6. 如果用户希望继续之前未完成的任务草稿，请返回 intent: "continue_draft"。

示例输出：
{"intent": "task", "confidence": 0.95, "reason": "用户明确要求添加一个新任务"}
"""

def classify_intent_with_qwen(user_input: str, model: str = "qwen-max") -> Optional[Dict[str, Any]]:
    system_prompt = build_system_prompt()
    
    try:
        # 使用QwenAdapter调用大模型
        qwen_adapter = QwenAdapter()
        
        # 构造messages格式
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input.strip()}
        ]
        
        # 调用generate_chat方法
        response = qwen_adapter.generate_chat(messages, temperature=0.1, max_tokens=200)
        
        if "error" in response:
            print(f"Qwen API error: {response['error']}")
            return {
                "intent": "ambiguous",
                "confidence": 0.0,
                "reason": f"系统异常: {response['error']}",
                "raw_input": user_input,
                "method": "error"
            }
        
        raw_output = response.get("content", "").strip()
        
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
            "reason": f"系统异常: {str(e)}",
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

def generate_clarification_options(intent_result: dict, user_input: str) -> list:
    """
    根据意图结果生成澄清选项
    """
    # 简化实现：根据意图类型生成不同的澄清选项
    if intent_result["intent"] == "task":
        return [
            {"option": "1", "text": "创建新任务"},
            {"option": "2", "text": "修改现有任务"},
            {"option": "3", "text": "查看任务状态"},
            {"option": "4", "text": "其他任务操作"}
        ]
    elif intent_result["intent"] == "query":
        return [
            {"option": "1", "text": "查询任务历史"},
            {"option": "2", "text": "查询任务统计"},
            {"option": "3", "text": "查询系统状态"},
            {"option": "4", "text": "其他查询"}
        ]
    else:
        return [
            {"option": "1", "text": "请详细说明您的需求"},
            {"option": "2", "text": "我想继续之前的任务"},
            {"option": "3", "text": "我想重新开始"}
        ]


# 注意：ConversationManager类已包含is_continue_request、execute_query等方法
# 以下是与外部意图识别集成的包装函数


def process_user_input_complete(user_input: str, conv_mgr: ConversationManager, user_id: str = "default_user") -> str:
    """
    完整处理用户输入，含草稿管理、状态机、追问、切换
    返回应答文本
    """
    # Step 0: 特殊意图优先检测 —— "继续草稿"
    if conv_mgr.is_continue_request(user_input):
        if conv_mgr.restore_latest_draft(user_id):
            return f"好的！我们继续刚才的任务。\n{conv_mgr.current_draft.last_question}"
        else:
            return "抱歉，我没有找到未完成的任务草稿。你可以重新开始一个任务吗？"

    # Step 1: 全局意图识别
    intent_result = classify_intent_with_qwen(user_input)
    
    # Step 2: 如果当前在追问中，但用户开启新意图 → 保存草稿并切换
    if conv_mgr.state == AgentState.COLLECTING_PARAMS:
        if intent_result["intent"] in ["task", "query", "system", "reflection"] and intent_result["confidence"] >= 0.75:
            # 保存当前草稿
            draft = conv_mgr.current_draft
            draft.updated_at = datetime.now()
            conv_mgr.save_draft(draft, user_id)
            
            # 清空当前状态，处理新意图
            conv_mgr.clear_draft()
            return handle_new_intent(intent_result, conv_mgr)
        
        # 如果是回答，则填充参数
        if intent_result["intent"] not in ["ambiguous", "chat"] or len(user_input.strip()) > 5:
            return handle_answer_to_question(user_input, conv_mgr)

    # Step 3: 空闲状态下处理新意图
    if conv_mgr.state == AgentState.IDLE:
        return handle_new_intent(intent_result, conv_mgr)
    
    # Step 4: 默认情况（如闲聊）
    return handle_idle_chat(user_input)


def handle_new_intent(intent_result: dict, conv_mgr: ConversationManager) -> str:
    """处理全新意图"""
    if intent_result["intent"] == "task":
        # 启动任务创建追问流程
        draft = TaskDraft(
            id=str(uuid.uuid4()),
            action_type="create_task",
            collected_params={},
            missing_params=["content", "due_date", "priority"],  # 示例字段
            last_question="请告诉我任务内容（例如：写周报）",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        conv_mgr.current_draft = draft
        conv_mgr.state = AgentState.COLLECTING_PARAMS
        return draft.last_question
    
    elif intent_result["intent"] == "query":
        # 直接执行查询（无追问）
        result = conv_mgr.execute_query(intent_result["raw_input"])
        conv_mgr.clear_draft()
        return result
    
    elif intent_result["intent"] == "chat":
        conv_mgr.clear_draft()
        return conv_mgr.generate_chat_response(intent_result["raw_input"])
    
    else:
        # system / reflection 等
        conv_mgr.clear_draft()
        return f"正在处理 {intent_result['intent']} 请求..."


def handle_answer_to_question(user_answer: str, conv_mgr: ConversationManager) -> str:
    """处理对追问的回答，更新草稿"""
    draft = conv_mgr.current_draft
    
    # 简化：假设每次回答填充一个字段（实际可用 NER 或 Qwen 解析）
    if "content" not in draft.collected_params:
        draft.collected_params["content"] = user_answer
        draft.missing_params.remove("content")
        draft.last_question = "请问截止时间是什么时候？（例如：明天下午3点）"
        draft.updated_at = datetime.now()
        return draft.last_question
    
    elif "due_date" not in draft.collected_params:
        draft.collected_params["due_date"] = user_answer
        draft.missing_params.remove("due_date")
        draft.last_question = "任务优先级是高、中还是低？"
        draft.updated_at = datetime.now()
        return draft.last_question
    
    else:
        # 所有参数收齐，创建任务
        task = conv_mgr.create_final_task(draft.collected_params)
        conv_mgr.clear_draft()
        return f"✅ 任务已创建：{task['content']}（截止：{task['due_date']}）"


def handle_idle_chat(user_input: str) -> str:
    """
    处理空闲状态下的闲聊
    """
    # 由于在实际使用中会通过ConversationManager调用，这里提供一个备用实现
    return f"很高兴与您聊天！您说：{user_input}"


# ===== 使用示例 =====
if __name__ == "__main__":
    # 示例使用
    conv_mgr = ConversationManager()
    user_id = "test_user_123"
    
    # 模拟对话流程
    print("开始对话...")
    # 1. 用户输入创建任务
    response = process_user_input_complete("我要创建一个任务", conv_mgr, user_id)
    print(f"AI: {response}")
    
    # 2. 用户回答任务内容
    response = process_user_input_complete("写周报", conv_mgr, user_id)
    print(f"AI: {response}")
    
    # 3. 用户中断并开始新话题
    response = process_user_input_complete("帮我查询一下天气", conv_mgr, user_id)
    print(f"AI: {response}")
    
    # 4. 用户要求继续
    response = process_user_input_complete("继续", conv_mgr, user_id)
    print(f"AI: {response}")
    
    # 5. 继续任务创建流程
    response = process_user_input_complete("明天下午5点", conv_mgr, user_id)
    print(f"AI: {response}")
    
    response = process_user_input_complete("高", conv_mgr, user_id)
    print(f"AI: {response}")
    print(f"当前状态: {conv_mgr.state}")
    if conv_mgr.current_draft:
        print(f"当前草稿参数: {conv_mgr.current_draft.collected_params}")
        print(f"缺失参数: {conv_mgr.current_draft.missing_params}")