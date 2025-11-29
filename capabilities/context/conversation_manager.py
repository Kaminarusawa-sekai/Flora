from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime
import uuid
import logging

from capabilities.context.interface import IConversationManagerCapability
from capabilities.registry import CapabilityRegistry
from common.types.draft import TaskDraft, AgentState
from external.repositories.draft_repo import DraftRepository

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ConversationManagerCapability(IConversationManagerCapability):
    """Conversation state and draft management capability"""
    def __init__(self):
        super().__init__()
        self.draft_repo = DraftRepository()
        self.state = AgentState.IDLE
        self.current_draft: Optional[TaskDraft] = None
        # Continue keywords for detecting "continue draft" requests
        self.continue_keywords = ["继续", "接着", "刚才", "之前", "未完成", "草稿"]
        # Pending tasks waiting for parameters: {task_id: TaskDraft}
        self.pending_tasks: Dict[str, TaskDraft] = {}
        # 记录每个用户的待处理任务: {user_id: {task_id: TaskDraft}}
        self.user_pending_tasks: Dict[str, Dict[str, TaskDraft]] = {}
        # 意图识别能力
        self.intent_router: Optional[IIntentRouterCapability] = None

    def initialize(self, config: Dict[str, Any] = None):
        """Initialize the capability"""
        from capabilities.cognition.intent_router import IIntentRouterCapability
        # 初始化IntentRouter
        self.intent_router = CapabilityRegistry.get_capability("intent_router", expected_type=IIntentRouterCapability)
        if not self.intent_router:
            logger.warning("IntentRouter capability not found, conversation manager may not work properly")
        else:
            logger.info("IntentRouter initialized successfully in ConversationManager")
    
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

    def handle_user_input(self, user_input: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        前台入口：处理用户输入并返回完整的处理结果
        这是新的主入口，agent_actor应该调用这个方法而不是process_user_input
        """
        logger.info(f"[ConversationManager] Processing user input: {user_input[:50]}...")

        # Step 1: 检查是否是继续草稿请求
        if self.is_continue_request(user_input):
            if self.restore_latest_draft(user_id):
                return {
                    "action": "continue_task",
                    "task_id": self.current_draft.id if self.current_draft else None,
                    "parameters": {},
                    "message": f"好的！我们继续刚才的任务。\n{self.current_draft.last_question}",
                    "needs_backend": False
                }
            else:
                return {
                    "action": "chat",
                    "task_id": None,
                    "parameters": {},
                    "message": "抱歉，我没有找到未完成的任务草稿。你可以重新开始一个任务吗？",
                    "needs_backend": False
                }

        # Step 2: 检查是否有等待参数补充的任务
        pending_tasks = self.get_pending_tasks(user_id)
        if pending_tasks:
            # 判断是否是参数补充
            target_task_id = self.identify_target_task(user_input, user_id)
            if target_task_id:
                # 补充参数
                is_complete, parameters = self.complete_task_parameters(target_task_id, user_input, user_id)

                if is_complete:
                    # 参数补充完成，通知后台继续执行
                    logger.info(f"[ConversationManager] Parameters complete for task {target_task_id}")
                    return {
                        "action": "parameter_completion",
                        "task_id": target_task_id,
                        "parameters": parameters,
                        "message": "参数已补充完成，正在继续执行任务...",
                        "needs_backend": True  # 需要通知后台继续执行
                    }
                else:
                    # 还有参数需要补充
                    draft = self.pending_tasks.get(target_task_id)
                    return {
                        "action": "parameter_completion",
                        "task_id": target_task_id,
                        "parameters": parameters,
                        "message": draft.last_question if draft else "请继续提供信息",
                        "needs_backend": False  # 还不需要后台介入
                    }

        # Step 3: 使用意图路由器判断意图
        if self.intent_router:
            intent_result = self.intent_router.classify_intent(user_input)
            from common.types.intent import IntentType

            # 如果意图不明确，需要澄清
            if intent_result.intent == IntentType.AMBIGUOUS:
                return {
                    "action": "clarification",
                    "task_id": None,
                    "parameters": {},
                    "message": "我不太确定你的意思，你能再详细说明一下吗？",
                    "needs_backend": False
                }

            # 如果是闲聊
            if intent_result.intent == IntentType.CHAT:
                return {
                    "action": "chat",
                    "task_id": None,
                    "parameters": {},
                    "message": self._generate_chat_response(user_input),
                    "needs_backend": False
                }

        # Step 4: 新任务，需要转发给后台
        return {
            "action": "new_task",
            "task_id": None,
            "parameters": {"user_input": user_input},
            "message": "正在处理你的请求...",
            "needs_backend": True  # 需要后台AgentActor处理
        }

    def is_parameter_completion(self, user_input: str, user_id: str = "default_user") -> bool:
        """判断用户输入是否是参数补充"""
        # 简单判断：如果有等待参数的任务，且输入不是新任务的关键词
        pending_tasks = self.get_pending_tasks(user_id)
        if not pending_tasks:
            return False

        # 使用LLM判断是否是参数补充
        return self._llm_is_parameter_answer(user_input, pending_tasks)

    def identify_target_task(self, user_input: str, user_id: str = "default_user") -> Optional[str]:
        """识别用户正在补充哪个任务的参数，返回task_id"""
        pending_tasks = self.get_pending_tasks(user_id)
        if not pending_tasks:
            return None

        # 如果只有一个等待参数的任务，直接返回
        if len(pending_tasks) == 1:
            return pending_tasks[0].id

        # 如果有多个，使用LLM判断
        return self._llm_identify_target_task(user_input, pending_tasks)

    def pause_task_for_parameters(self, task_id: str, missing_params: List[str],
                                  task_context: Dict[str, Any], user_id: str = "default_user") -> str:
        """
        后台调用：暂停任务链，等待用户补充参数
        """
        logger.info(f"[ConversationManager] Pausing task {task_id} for parameters: {missing_params}")

        # 创建draft
        draft = TaskDraft(
            id=task_id,
            action_type="task_execution",
            collected_params=task_context.get("collected_params", {}),
            missing_params=missing_params,
            last_question=self._generate_parameter_question(missing_params[0], task_context),
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 保存到pending_tasks
        self.pending_tasks[task_id] = draft

        # 按用户分组保存
        if user_id not in self.user_pending_tasks:
            self.user_pending_tasks[user_id] = {}
        self.user_pending_tasks[user_id][task_id] = draft

        # 保存到数据库
        self.save_draft(draft, user_id)

        return draft.last_question

    def get_pending_tasks(self, user_id: str = "default_user") -> List[TaskDraft]:
        """获取用户所有等待参数补充的任务"""
        if user_id in self.user_pending_tasks:
            return list(self.user_pending_tasks[user_id].values())
        return []

    def complete_task_parameters(self, task_id: str, user_input: str,
                                 user_id: str = "default_user") -> Tuple[bool, Dict[str, Any]]:
        """
        补充任务参数

        Returns:
            Tuple[is_complete, parameters]:
            - is_complete: 参数是否已全部补充完成
            - parameters: 已补充的参数字典
        """
        # 优先从用户的待处理任务中查找
        draft = None
        if user_id in self.user_pending_tasks and task_id in self.user_pending_tasks[user_id]:
            draft = self.user_pending_tasks[user_id][task_id]
        elif task_id in self.pending_tasks:
            draft = self.pending_tasks.get(task_id)

        if not draft:
            logger.warning(f"[ConversationManager] Task {task_id} not found in pending tasks")
            return False, {}

        # 提取当前缺失参数的值
        if draft.missing_params:
            current_param = draft.missing_params[0]
            # 使用LLM提取参数值
            param_value = self._llm_extract_parameter_value(user_input, current_param, draft.collected_params)

            # 保存参数
            draft.collected_params[current_param] = param_value
            draft.missing_params.remove(current_param)
            draft.updated_at = datetime.now()

            # 检查是否还有缺失参数
            if draft.missing_params:
                # 还有参数需要补充
                next_param = draft.missing_params[0]
                draft.last_question = self._generate_parameter_question(next_param, draft.collected_params)
                self.save_draft(draft, user_id)
                return False, draft.collected_params
            else:
                # 所有参数已补充完成
                logger.info(f"[ConversationManager] All parameters collected for task {task_id}")
                # 从pending_tasks中移除
                if task_id in self.pending_tasks:
                    del self.pending_tasks[task_id]
                # 从用户待处理任务中移除
                if user_id in self.user_pending_tasks and task_id in self.user_pending_tasks[user_id]:
                    del self.user_pending_tasks[user_id][task_id]
                return True, draft.collected_params

        return True, draft.collected_params
    
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

    # ============= LLM辅助方法 =============

    def _llm_is_parameter_answer(self, user_input: str, pending_tasks: List[TaskDraft]) -> bool:
        """使用LLM判断用户输入是否是对参数问题的回答"""
        try:
            from capabilities import get_capability
            from capabilities.llm.interface import ILLMCapability

            llm = get_capability("qwen", expected_type=ILLMCapability)
            if not llm:
                # 回退：简单判断
                return len(user_input) < 100 and not any(kw in user_input for kw in ["帮我", "查询", "执行"])

            # 构建prompt
            tasks_info = "\n".join([
                f"- 任务 {i+1}: {draft.last_question}"
                for i, draft in enumerate(pending_tasks)
            ])

            prompt = f"""你是一个智能助手。请判断用户输入是否是对以下问题的回答。

当前等待用户回答的问题：
{tasks_info}

用户输入：{user_input}

请严格按以下JSON格式输出：
{{
  "is_answer": true/false,
  "reasoning": "简要说明判断依据"
}}"""

            result = llm.generate(prompt, parse_json=True, max_tokens=200, temperature=0.2)
            return result.get("is_answer", False)

        except Exception as e:
            logger.warning(f"LLM parameter answer detection failed: {e}")
            # 回退：简单判断
            return len(user_input) < 100

    def _llm_identify_target_task(self, user_input: str, pending_tasks: List[TaskDraft]) -> Optional[str]:
        """使用LLM识别用户正在补充哪个任务的参数"""
        try:
            from capabilities import get_capability
            from capabilities.llm.interface import ILLMCapability

            llm = get_capability("qwen", expected_type=ILLMCapability)
            if not llm:
                # 回退：返回第一个
                return pending_tasks[0].id if pending_tasks else None

            # 构建prompt
            tasks_info = "\n".join([
                f"- task_id: {draft.id}, 问题: {draft.last_question}"
                for draft in pending_tasks
            ])

            prompt = f"""你是一个智能助手。请判断用户的回答是针对哪个任务的。

等待回答的任务：
{tasks_info}

用户输入：{user_input}

请严格按以下JSON格式输出：
{{
  "task_id": "任务ID",
  "reasoning": "简要说明判断依据"
}}"""

            result = llm.generate(prompt, parse_json=True, max_tokens=200, temperature=0.2)
            return result.get("task_id")

        except Exception as e:
            logger.warning(f"LLM target task identification failed: {e}")
            # 回退：返回第一个
            return pending_tasks[0].id if pending_tasks else None

    def _llm_extract_parameter_value(self, user_input: str, param_name: str,
                                    collected_params: Dict[str, Any]) -> Any:
        """使用LLM从用户输入中提取参数值"""
        try:
            from capabilities import get_capability
            from capabilities.llm.interface import ILLMCapability

            llm = get_capability("qwen", expected_type=ILLMCapability)
            if not llm:
                # 回退：直接返回用户输入
                return user_input

            # 构建prompt
            context_info = "\n".join([
                f"- {key}: {value}"
                for key, value in collected_params.items()
            ])

            prompt = f"""你是一个智能助手。请从用户输入中提取参数值。

需要提取的参数名：{param_name}
已收集的上下文：
{context_info}

用户输入：{user_input}

请提取参数值并按以下JSON格式输出：
{{
  "value": "提取的参数值",
  "reasoning": "简要说明提取依据"
}}"""

            result = llm.generate(prompt, parse_json=True, max_tokens=300, temperature=0.2)
            return result.get("value", user_input)

        except Exception as e:
            logger.warning(f"LLM parameter extraction failed: {e}")
            # 回退：直接返回用户输入
            return user_input

    def _generate_parameter_question(self, param_name: str, context: Dict[str, Any]) -> str:
        """生成询问参数的问题"""
        # 简单实现：根据参数名生成问题
        question_templates = {
            "url": "请提供URL地址",
            "api_key": "请提供API密钥",
            "workflow_id": "请提供工作流ID",
            "inputs": "请提供输入参数（JSON格式）",
            "query": "请提供查询语句",
            "data": "请提供数据内容",
            "content": "请提供具体内容",
            "user": "请提供用户标识",
        }

        question = question_templates.get(param_name, f"请提供参数 {param_name} 的值")
        return f"{question}："

# Register the capability
from capabilities.registry import capability_registry
capability_registry.register_class("conversation_manager", ConversationManagerCapability)
