from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from .interface import IDialogStateManagerCapability
from common import (
    DialogStateDTO,
    TaskDraftDTO,
    TaskSummary,
    IntentRecognitionResultDTO,
    IntentType,
    EntityDTO,
    UserInputDTO
)
from time import timezone
from ..llm.interface import ILLMCapability
from external.database.dialog_state_repo import DialogStateRepository

class CommonDialogState(IDialogStateManagerCapability):
    """对话状态管理器 - 维护全局对话状态"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化对话状态管理器"""
        self.logger.info("初始化对话状态管理器")
        self.config = config
        # 获取LLM能力
        self._llm = None
        self.dialog_repo = DialogStateRepository()
        self.logger.info("对话状态管理器初始化完成")
    
    @property
    def llm(self):
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
    
    def shutdown(self) -> None:
        """关闭对话状态管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "dialog_management"
    
    def get_or_create_dialog_state(self, session_id: str, user_id: str) -> DialogStateDTO:
        """获取或创建对话状态
        
        Args:
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            对话状态DTO
        """
        # 从存储中获取对话状态
        state = self.dialog_repo.get_dialog_state(session_id)
        
        # 如果不存在，创建新的对话状态
        if not state:
            state = DialogStateDTO(
                session_id=session_id,
                user_id=user_id,  # 关联到用户
                current_intent=None,
                active_task_draft=None,
                active_task_execution=None,
                pending_tasks=[],
                recent_tasks=[],
                last_mentioned_task_id=None,
                is_in_idle_mode=False
            )
            self.dialog_repo.save_dialog_state(state)
        else:
            # 校验 user_id 一致性
            if state.user_id != user_id:
                # 更新 user_id
                state.user_id = user_id
                self.dialog_repo.update_dialog_state(state)
        
        return state
    
    def update_dialog_state(self, state: DialogStateDTO) -> bool:
        """更新对话状态
        
        Args:
            state: 对话状态DTO
            
        Returns:
            是否更新成功
        """
        return self.dialog_repo.update_dialog_state(state)
    
    def set_active_draft(self, session_id: str, draft: Optional[TaskDraftDTO]) -> DialogStateDTO:
        """设置活跃的任务草稿
        
        Args:
            session_id: 会话ID
            draft: 任务草稿DTO，None表示清除活跃草稿
            
        Returns:
            更新后的对话状态
        """
        # 尝试从现有状态获取 user_id，如果不存在则生成临时 user_id
        existing_state = self.dialog_repo.get_dialog_state(session_id)
        user_id = existing_state.user_id if existing_state else f"temp_{session_id}"
        state = self.get_or_create_dialog_state(session_id, user_id)
        state.active_task_draft = draft
        self.update_dialog_state(state)
        return state
    
    def set_active_execution(self, session_id: str, task_id: Optional[str]) -> DialogStateDTO:
        """设置活跃的任务执行
        
        Args:
            session_id: 会话ID
            task_id: 任务执行ID，None表示清除活跃执行
            
        Returns:
            更新后的对话状态
        """
        # 尝试从现有状态获取 user_id，如果不存在则生成临时 user_id
        existing_state = self.dialog_repo.get_dialog_state(session_id)
        user_id = existing_state.user_id if existing_state else f"temp_{session_id}"
        state = self.get_or_create_dialog_state(session_id, user_id)
        state.active_task_execution = task_id
        self.update_dialog_state(state)
        return state
    
    def add_recent_task(self, session_id: str, task_summary: TaskSummary) -> DialogStateDTO:
        """添加最近任务到对话状态
        
        Args:
            session_id: 会话ID
            task_summary: 任务摘要
            
        Returns:
            更新后的对话状态
        """
        # 尝试从现有状态获取 user_id，如果不存在则生成临时 user_id
        existing_state = self.dialog_repo.get_dialog_state(session_id)
        user_id = existing_state.user_id if existing_state else f"temp_{session_id}"
        state = self.get_or_create_dialog_state(session_id, user_id)
        
        # 限制最近任务的数量
        MAX_RECENT_TASKS = 5
        state.recent_tasks.insert(0, task_summary)
        if len(state.recent_tasks) > MAX_RECENT_TASKS:
            state.recent_tasks = state.recent_tasks[:MAX_RECENT_TASKS]
        
        self.update_dialog_state(state)
        return state
    
    def set_last_mentioned_task(self, session_id: str, task_id: Optional[str]) -> DialogStateDTO:
        """设置最后提及的任务
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        # 尝试从现有状态获取 user_id，如果不存在则生成临时 user_id
        existing_state = self.dialog_repo.get_dialog_state(session_id)
        user_id = existing_state.user_id if existing_state else f"temp_{session_id}"
        state = self.get_or_create_dialog_state(session_id, user_id)
        state.last_mentioned_task_id = task_id
        self.update_dialog_state(state)
        return state
    
    def get_last_mentioned_task(self, session_id: str) -> Optional[str]:
        """获取最后提及的任务
        
        Args:
            session_id: 会话ID
            
        Returns:
            最后提及的任务ID
        """
        # 尝试从现有状态获取 user_id，如果不存在则生成临时 user_id
        existing_state = self.dialog_repo.get_dialog_state(session_id)
        user_id = existing_state.user_id if existing_state else f"temp_{session_id}"
        state = self.get_or_create_dialog_state(session_id, user_id)
        return state.last_mentioned_task_id
    
    def add_pending_task(self, session_id: str, task_id: str) -> DialogStateDTO:
        """添加待处理任务到任务栈
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        # 尝试从现有状态获取 user_id，如果不存在则生成临时 user_id
        existing_state = self.dialog_repo.get_dialog_state(session_id)
        user_id = existing_state.user_id if existing_state else f"temp_{session_id}"
        state = self.get_or_create_dialog_state(session_id, user_id)
        if task_id not in state.pending_tasks:
            state.pending_tasks.append(task_id)
            self.update_dialog_state(state)
        return state
    
    def remove_pending_task(self, session_id: str, task_id: str) -> DialogStateDTO:
        """从任务栈中移除待处理任务
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            
        Returns:
            更新后的对话状态
        """
        # 尝试从现有状态获取 user_id，如果不存在则生成临时 user_id
        existing_state = self.dialog_repo.get_dialog_state(session_id)
        user_id = existing_state.user_id if existing_state else f"temp_{session_id}"
        state = self.get_or_create_dialog_state(session_id, user_id)
        if task_id in state.pending_tasks:
            state.pending_tasks.remove(task_id)
            self.update_dialog_state(state)
        return state
    

    ##TODO:1.填槽使用槽位管理的函数，2.填槽前查询已知信息（放在event里）
    def process_intent_result(
        self,
        session_id: str,
        intent_result: IntentRecognitionResultDTO,
        user_input: Optional[UserInputDTO] = None
    ) -> DialogStateDTO:
        """主入口：根据意图识别结果更新对话状态，可能触发澄清、草稿填充、意图修正等
        
        Args:
            session_id: 会话ID
            intent_result: 意图识别结果
            user_input: 用户输入（可选，用于日志或澄清）
            
        Returns:
            更新后的对话状态
        """
        # 尝试从现有状态获取 user_id，如果不存在则生成临时 user_id
        existing_state = self.dialog_repo.get_dialog_state(session_id)
        user_id = existing_state.user_id if existing_state else f"temp_{session_id}"
        state = self.get_or_create_dialog_state(session_id, user_id)
        
        # 1. 【意图修正】基于上下文调整主意图
        corrected_intent = self._resolve_ambiguous_intent(intent_result, state)
        
        # 2. 【草稿管理】决定是否创建/更新/清除草稿
        if corrected_intent in [IntentType.CREATE_TASK, IntentType.MODIFY_TASK, IntentType.SET_SCHEDULE]:
            if state.active_task_draft is None:
                # 创建新草稿
                draft = TaskDraftDTO(task_type=corrected_intent.value, slots={})
                state.active_task_draft = draft
            # 否则：复用现有草稿（用户可能在多轮填充）
        else:
            # 非草稿类意图：可选择保留或清除草稿（根据策略）
            # 例如：QUERY 不影响草稿，DELETE 可能清除
            pass

        # 4. 【指代消解】如果有代词，尝试解析指代的任务
        if state.active_task_draft and user_input and user_input.utterance:
            resolved_id = self._resolve_pronoun_reference(user_input.utterance, state)
            if resolved_id:
                state.last_mentioned_task_id = resolved_id
                # 将该任务信息注入草稿（如 title）
                target_task = self._find_task_by_id(resolved_id, state.recent_tasks)
                if target_task:
                    state.active_task_draft.slots.setdefault("title", target_task.title)

        # 6. 【歧义处理】标记是否需要澄清（供 Orchestrator 使用）
        if intent_result.is_ambiguous:
            state.requires_clarification = True
            state.clarification_context = {
                "original_utterance": user_input.utterance if user_input else "",
                "candidate_intents": [
                    (intent.value, score) for intent, score in intent_result.alternative_intents
                ],
                "primary_intent": corrected_intent.value
            }
            # 生成澄清问题
            state.clarification_message = self._generate_clarification_message(state.clarification_context)
        else:
            state.requires_clarification = False
            state.clarification_context = None
            state.clarification_message = None

        # 7. 更新当前意图
        state.current_intent = corrected_intent.value

        # 8. 更新最后更新时间
        state.last_updated = datetime.now(timezone.utc)

        # 9. 持久化
        self.update_dialog_state(state)
        return state
    
    def _resolve_ambiguous_intent(
        self,
        intent_result: IntentRecognitionResultDTO,
        state: DialogStateDTO
    ) -> IntentType:
        """基于对话状态修正意图（例如区分 RESUME vs RESUME_TASK）
        
        Args:
            intent_result: 意图识别结果
            state: 当前对话状态
            
        Returns:
            修正后的意图
        """
        primary = intent_result.primary_intent

        # 场景1: 用户说“继续”，但系统有中断任务 → 应为 RESUME (恢复中断)
        if primary == IntentType.RESUME_TASK:
            # 检查是否有中断任务（假设 recent_tasks 中有状态信息）
            has_interrupted = any(
                getattr(task, 'status', None) == "INTERRUPTED" for task in state.recent_tasks
            )
            if has_interrupted:
                return IntentType.RESUME_INTERRUPTED  # 转为“恢复中断”

        # 场景2: “取消” + 有活跃执行 → CANCEL_TASK；否则可能是取消草稿
        if primary == IntentType.CANCEL_TASK:
            if state.active_task_execution:
                return IntentType.CANCEL_TASK
            elif state.active_task_draft:
                # 可视为放弃草稿（不生成任务）
                pass  # 保持 CANCEL，由 Orchestrator 处理

        # 其他上下文修正规则...

        return primary
    
    def cleanup_expired_sessions(self, max_idle_minutes: int = 30) -> int:
        """清理超过 N 分钟未活动的会话
        
        Args:
            max_idle_minutes: 最大空闲分钟数
            
        Returns:
            清理的会话数量
        """
        # 假设 DialogStateDTO 有 last_updated 字段
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_idle_minutes)
        expired_ids = self.dialog_repo.find_expired_sessions(cutoff)
        for sid in expired_ids:
            self.dialog_repo.delete_dialog_state(sid)
        return len(expired_ids)
    
    def _has_pronouns(self, utterance: str) -> bool:
        """检查文本中是否包含代词
        
        Args:
            utterance: 用户输入文本
            
        Returns:
            是否包含代词
        """
        pronouns = ["它", "这个", "那个", "这些", "那些", "他", "她"]
        return any(pronoun in utterance for pronoun in pronouns)
    
    def _resolve_pronoun_reference(self, utterance: str, state: DialogStateDTO) -> Optional[str]:
        """指代消解：解析文本中的代词指代的任务
        
        Args:
            utterance: 用户输入文本
            state: 当前对话状态
            
        Returns:
            解析出的任务ID，或None
        """
        if not self._has_pronouns(utterance):
            return None
        
        recent_tasks_str = "\n".join(
            f"- ID: {t.task_id}, 标题: {t.title}, 状态: {t.status}"
            for t in state.recent_tasks[:3]
        )
        prompt = f"""
你是一个任务助手。用户说：“{utterance}”。
以下是最近的任务列表：
{recent_tasks_str}

请返回最可能被指代的任务ID（仅返回ID字符串，如 "task_123"），如果没有匹配，返回 "none"。
"""
        try:
            task_id = self.llm.generate(prompt).strip()
            return task_id if task_id != "none" else None
        except:
            return None
    
    def _generate_clarification_message(self, context: dict) -> str:
        """生成澄清问题：当意图模糊时，生成自然的澄清问题
        
        Args:
            context: 澄清上下文
            
        Returns:
            澄清问题字符串
        """
        candidates = ", ".join(intent for intent, _ in context["candidate_intents"])
        prompt = f"""
        用户输入："{context['original_utterance']}"
        系统识别出多个可能意图：{candidates}

        请用一句简洁友好的中文提问，帮助用户澄清真实意图。
        例如："你是想创建新任务，还是修改已有任务？"

        只返回问题，不要解释。
        """
        return self.llm.generate(prompt).strip()
    
    def _find_task_by_id(self, task_id: str, recent_tasks: List[TaskSummary]) -> Optional[TaskSummary]:
        """根据任务ID查找最近任务
        
        Args:
            task_id: 任务ID
            recent_tasks: 最近任务列表
            
        Returns:
            找到的任务，或None
        """
        for task in recent_tasks:
            if task.task_id == task_id:
                return task
        return None
    
    def set_waiting_for_confirmation(self, dialog_state: DialogStateDTO, action: str, payload: dict) -> DialogStateDTO:
        """设置等待确认状态
        
        Args:
            dialog_state: 对话状态DTO
            action: 等待确认的动作类型
            payload: 确认所需的上下文数据
            
        Returns:
            更新后的对话状态
        """
        dialog_state.waiting_for_confirmation = True
        dialog_state.confirmation_action = action
        dialog_state.confirmation_payload = payload
        return dialog_state
    
    def clear_waiting_for_confirmation(self, dialog_state: DialogStateDTO) -> DialogStateDTO:
        """清除等待确认状态
        
        Args:
            dialog_state: 对话状态DTO
            
        Returns:
            更新后的对话状态
        """
        dialog_state.waiting_for_confirmation = False
        dialog_state.confirmation_action = None
        dialog_state.confirmation_payload = None
        return dialog_state
    
    def clear_active_draft(self, dialog_state: DialogStateDTO) -> DialogStateDTO:
        """清除活跃的任务草稿
        
        Args:
            dialog_state: 对话状态DTO
            
        Returns:
            更新后的对话状态
        """
        dialog_state.active_task_draft = None
        return dialog_state