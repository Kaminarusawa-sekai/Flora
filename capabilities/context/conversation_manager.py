from typing import Dict, Optional, Any, List
from datetime import datetime
import uuid
from capabilities.capability_base import CapabilityBase
from capabilities.registry import CapabilityRegistry
from common.types.draft import TaskDraft, AgentState
from external.repositories.draft_repo import DraftRepository

class IConversationManagerCapability(CapabilityBase):
    """Interface for conversation management capability"""
    def process_user_input(self, user_input: str, user_id: str = "default_user") -> str:
        """Process user input with draft management"""
        raise NotImplementedError
    
    def is_continue_request(self, user_input: str) -> bool:
        """Check if user wants to continue draft"""
        raise NotImplementedError
    
    def restore_latest_draft(self, user_id: str = "default_user") -> bool:
        """Restore latest draft"""
        raise NotImplementedError
    
    def save_draft(self, draft: TaskDraft, user_id: str = "default_user"):
        """Save current draft"""
        raise NotImplementedError
    
    def clear_draft(self):
        """Clear current draft"""
        raise NotImplementedError

class ConversationManagerCapability(IConversationManagerCapability):
    """Conversation state and draft management capability"""
    def __init__(self):
        super().__init__()
        self.draft_repo = DraftRepository()
        self.state = AgentState.IDLE
        self.current_draft: Optional[TaskDraft] = None
        # Continue keywords for detecting "continue draft" requests
        self.continue_keywords = ["继续", "接着", "刚才", "之前", "未完成", "草稿"]
    
    def initialize(self, config: Dict[str, Any] = None):
        """Initialize the capability"""
        pass
    
    def shutdown(self):
        """Shutdown the capability"""
        pass
    
    def get_capability_type(self) -> str:
        """Return capability type"""
        return "context"
    
    def is_continue_request(self, user_input: str) -> bool:
        """Check if user wants to continue draft"""
        return any(kw in user_input for kw in self.continue_keywords)
    
    def restore_latest_draft(self, user_id: str = "default_user") -> bool:
        """Restore latest draft"""
        draft = self.draft_repo.get_latest_draft(user_id)
        if draft:
            self.current_draft = draft
            self.state = AgentState.COLLECTING_PARAMS
            return True
        return False
    
    def save_draft(self, draft: TaskDraft, user_id: str = "default_user"):
        """Save current draft"""
        self.draft_repo.save_draft(draft, user_id)
        self.state = AgentState.DRAFT_SAVED
    
    def clear_draft(self):
        """Clear current draft"""
        self.current_draft = None
        self.state = AgentState.IDLE
    
    def process_user_input(self, user_input: str, user_id: str = "default_user") -> str:
        """Process user input with draft management"""
        # Step 0: Check if user wants to continue draft
        if self.is_continue_request(user_input):
            if self.restore_latest_draft(user_id):
                return f"好的！我们继续刚才的任务。\n{self.current_draft.last_question}"
            else:
                return "抱歉，我没有找到未完成的任务草稿。你可以重新开始一个任务吗？"
        
        # Step 1: Get intent from intent router capability
        intent_router = CapabilityRegistry.get_capability("intent_router")
        intent_result = intent_router.classify_intent(user_input)
        
        # Step 2: If currently collecting params but user starts new intent -> save draft and switch
        if self.state == AgentState.COLLECTING_PARAMS:
            from common.types.intent import IntentType
            if intent_result.intent in [IntentType.TASK, IntentType.QUERY, IntentType.SYSTEM, IntentType.REFLECTION] and intent_result.confidence >= 0.75:
                # Save current draft
                draft = self.current_draft
                draft.updated_at = datetime.now()
                self.save_draft(draft, user_id)
                
                # Clear current state and handle new intent
                self.clear_draft()
                return self._handle_new_intent(intent_result)
            
            # If it's an answer, fill params
            if intent_result.intent not in [IntentType.AMBIGUOUS, IntentType.CHAT] or len(user_input.strip()) > 5:
                return self._handle_answer_to_question(user_input)
        
        # Step 3: Handle new intent when idle
        if self.state == AgentState.IDLE:
            return self._handle_new_intent(intent_result)
        
        # Step 4: Default case (e.g., chat)
        return self._handle_idle_chat(user_input)
    
    def _handle_new_intent(self, intent_result) -> str:
        """Handle new intent"""
        from common.types.intent import IntentType
        
        if intent_result.intent == IntentType.TASK:
            # Start task creation flow
            draft = TaskDraft(
                id=str(uuid.uuid4()),
                action_type="create_task",
                collected_params={},
                missing_params=["content", "due_date", "priority"],
                last_question="请告诉我任务内容（例如：写周报）",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            self.current_draft = draft
            self.state = AgentState.COLLECTING_PARAMS
            return draft.last_question
        
        elif intent_result.intent == IntentType.QUERY:
            # Execute query directly
            result = self._execute_query(intent_result.raw_input)
            self.clear_draft()
            return result
        
        elif intent_result.intent == IntentType.CHAT:
            self.clear_draft()
            return self._generate_chat_response(intent_result.raw_input)
        
        else:
            # system / reflection etc.
            self.clear_draft()
            return f"正在处理 {intent_result.intent.value} 请求..."
    
    def _handle_answer_to_question(self, user_answer: str) -> str:
        """Handle answer to question"""
        draft = self.current_draft
        
        # Simple implementation: assume each answer fills one field
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
            # All params collected, create task
            task = self._create_final_task(draft.collected_params)
            self.clear_draft()
            return f"✅ 任务已创建：{task['content']}（截止：{task['due_date']}）"
    
    # Helper methods (to be implemented with actual functionality)
    def _create_final_task(self, collected_params: Dict[str, Any]) -> Dict[str, Any]:
        """Create final task"""
        return collected_params
    
    def _execute_query(self, query: str) -> str:
        """Execute query"""
        return f"查询结果：{query}"
    
    def _generate_chat_response(self, chat_input: str) -> str:
        """Generate chat response"""
        return f"聊天回复：{chat_input}"
    
    def _handle_idle_chat(self, user_input: str) -> str:
        """Handle idle chat"""
        return self._generate_chat_response(user_input)

# Register the capability
from capabilities.registry import capability_registry
capability_registry.register_class("conversation_manager", ConversationManagerCapability)
