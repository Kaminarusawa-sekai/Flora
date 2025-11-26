from enum import Enum
from typing import Dict, Optional, Any
from datetime import datetime
import uuid
import json

# 导入必要的类型和类
from .task_draft import TaskDraft

# 定义继续请求的关键词
CONTINUE_KEYWORDS = ["继续", "接着", "刚才", "之前", "未完成", "草稿"]

class AgentState(Enum):
    IDLE = "idle"                          # 空闲，等待新输入
    COLLECTING_PARAMS = "collecting_params"  # 正在追问参数
    DRAFT_SAVED = "draft_saved"            # 草稿已保存（因中断）


class ConversationState:
    def __init__(self):
        self.awaiting_task_params = False          # 是否在等待任务参数
        self.pending_task_draft = {}               # 临时任务草稿
        self.last_question = ""                    # 上次问的问题（用于判断是否相关）
        self.task_context = None                   # 当前任务上下文（如 task_id）


class ConversationManager:
    def __init__(self):
        self.state = AgentState.IDLE
        self.current_draft: Optional[TaskDraft] = None
        self.saved_drafts: Dict[str, TaskDraft] = {}  # user_id → draft（单用户可简化为一个）
    
    def save_draft(self, draft: TaskDraft):
        """保存草稿（覆盖最新）"""
        self.saved_drafts["latest"] = draft
        self.state = AgentState.DRAFT_SAVED
    
    def restore_latest_draft(self) -> Optional[TaskDraft]:
        """恢复最近草稿"""
        draft = self.saved_drafts.get("latest")
        if draft:
            self.current_draft = draft
            self.state = AgentState.COLLECTING_PARAMS
            del self.saved_drafts["latest"]  # 取出后清除，避免重复恢复
        return draft
    
    def clear_draft(self):
        self.current_draft = None
        self.state = AgentState.IDLE

    def is_continue_request(self, user_input: str) -> bool:
        """
        判断是否为“继续草稿”请求
        """
        # 兜底：关键词匹配
        return any(kw in user_input for kw in CONTINUE_KEYWORDS)
    
    def process_user_input_complete(self, user_input: str) -> str:
        """
        完整处理用户输入，含草稿管理、状态机、追问、切换
        返回应答文本
        """
        # Step 0: 特殊意图优先检测 —— “继续草稿”
        if self.is_continue_request(user_input):
            if self.restore_latest_draft():
                return f"好的！我们继续刚才的任务。\n{self.current_draft.last_question}"
            else:
                return "抱歉，我没有找到未完成的任务草稿。你可以重新开始一个任务吗？"

        # Step 1: 全局意图识别
        # 注意：这里需要调用外部的意图识别函数，暂时返回默认值
        intent_result = {
            "intent": "task",
            "confidence": 0.8,
            "reason": "默认任务意图",
            "raw_input": user_input
        }
        
        # Step 2: 如果当前在追问中，但用户开启新意图 → 保存草稿并切换
        if self.state == AgentState.COLLECTING_PARAMS:
            if intent_result["intent"] in ["task", "query", "system", "reflection"] and intent_result["confidence"] >= 0.75:
                # 保存当前草稿
                draft = self.current_draft
                draft.updated_at = datetime.now()
                self.save_draft(draft)
                
                # 清空当前状态，处理新意图
                self.clear_draft()
                return self.handle_new_intent(intent_result)
            
            # 如果是回答，则填充参数
            if intent_result["intent"] not in ["ambiguous", "chat"] or len(user_input.strip()) > 5:
                return self.handle_answer_to_question(user_input)

        # Step 3: 空闲状态下处理新意图
        if self.state == AgentState.IDLE:
            return self.handle_new_intent(intent_result)
        
        # Step 4: 默认情况（如闲聊）
        return self.handle_idle_chat(user_input)

    def handle_new_intent(self, intent_result: dict) -> str:
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
            self.current_draft = draft
            self.state = AgentState.COLLECTING_PARAMS
            return draft.last_question
        
        elif intent_result["intent"] == "query":
            # 直接执行查询（无追问）
            result = self.execute_query(intent_result["raw_input"])
            self.clear_draft()
            return result
        
        elif intent_result["intent"] == "chat":
            self.clear_draft()
            return self.generate_chat_response(intent_result["raw_input"])
        
        else:
            # system / reflection 等
            self.clear_draft()
            return f"正在处理 {intent_result['intent']} 请求..."

    def handle_answer_to_question(self, user_answer: str) -> str:
        """处理对追问的回答，更新草稿"""
        draft = self.current_draft
        
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
            task = self.create_final_task(draft.collected_params)
            self.clear_draft()
            return f"✅ 任务已创建：{task['content']}（截止：{task['due_date']}）"
    
    # 辅助函数，需要在实际使用时替换为真实实现
    def create_final_task(self, collected_params: Dict[str, Any]) -> Dict[str, Any]:
        """创建最终任务"""
        return collected_params
    
    def execute_query(self, query: str) -> str:
        """执行查询"""
        return f"查询结果：{query}"
    
    def generate_chat_response(self, chat_input: str) -> str:
        """生成聊天回复"""
        return f"聊天回复：{chat_input}"
    
    def handle_idle_chat(self, user_input: str) -> str:
        """处理空闲状态下的聊天"""
        return self.generate_chat_response(user_input)