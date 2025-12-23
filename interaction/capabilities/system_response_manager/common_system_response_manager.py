from typing import Dict, Any, Optional, List
from .interface import ISystemResponseManagerCapability
from common import (
    SystemResponseDTO,
    SuggestedActionDTO,
    ActionType,
    TaskStatusSummary
)
from ..llm.interface import ILLMCapability

class CommonSystemResponse(ISystemResponseManagerCapability):
    """系统响应管理器 - 统一生成系统响应，包括文本和结构化数据"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化系统响应管理器"""
        self.config = config
        self._llm = None
        
    @property
    def llm(self):
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
    
    def shutdown(self) -> None:
        """关闭系统响应管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "response_generation"
    
    def generate_response(self, session_id: str, response_text: str, 
                         suggested_actions: List[SuggestedActionDTO] = None, 
                         task_status: Optional[TaskStatusSummary] = None, 
                         requires_input: bool = False, 
                         awaiting_slot: Optional[str] = None, 
                         display_data: Optional[Dict[str, Any]] = None) -> SystemResponseDTO:
        """生成系统响应
        
        Args:
            session_id: 会话ID
            response_text: 响应文本
            suggested_actions: 建议操作列表
            task_status: 任务状态摘要
            requires_input: 是否需要用户输入
            awaiting_slot: 正在等待的槽位
            display_data: 结构化展示数据
            
        Returns:
            系统响应DTO
        """
        return SystemResponseDTO(
            session_id=session_id,
            response_text=response_text,
            suggested_actions=suggested_actions or [],
            task_status=task_status,
            requires_input=requires_input,
            awaiting_slot=awaiting_slot,
            display_data=display_data
        )
    
    def generate_task_creation_response(self, session_id: str, task_id: str, task_title: str) -> SystemResponseDTO:
        """生成任务创建成功的响应
        
        Args:
            session_id: 会话ID
            task_id: 任务ID
            task_title: 任务标题
            
        Returns:
            系统响应DTO
        """
        fallback_text = f"任务 '{task_title}' 已成功创建，任务ID: {task_id}"
        
        # 使用 LLM 增强响应文本
        enhanced_text = self._enhance_text_with_llm(
            base_info={
                "task_title": task_title,
                "task_id": task_id,
                "fallback_text": fallback_text
            },
            context_type="task_creation"
        )
        
        # 生成建议操作
        suggested_actions = [
            SuggestedActionDTO(
                type=ActionType.QUERY,
                title="查看任务状态",
                payload=f"QUERY_TASK_{task_id}"
            ),
            SuggestedActionDTO(
                type=ActionType.CANCEL,
                title="取消任务",
                payload=f"CANCEL_TASK_{task_id}"
            )
        ]
        
        return self.generate_response(
            session_id=session_id,
            response_text=enhanced_text,
            suggested_actions=suggested_actions,
            requires_input=False
        )
    
    def generate_task_status_response(self, session_id: str, task_status_info: Dict[str, Any]) -> SystemResponseDTO:
        """生成任务状态响应
        
        Args:
            session_id: 会话ID
            task_status_info: 任务状态信息
            
        Returns:
            系统响应DTO
        """
        task_id = task_status_info["task_id"]
        status = task_status_info["status"]
        title = task_status_info["title"]
        progress = task_status_info["progress"]
        error_summary = task_status_info.get("error_summary", "")
        
        # 原始 fallback 文本（用于 LLM 失败时回退）
        if status == "RUNNING":
            fallback_text = f"任务 '{title}' 正在运行中，进度: {int(progress * 100)}%"
        elif status == "COMPLETED":
            fallback_text = f"任务 '{title}' 已成功完成"
        elif status == "FAILED":
            fallback_text = f"任务 '{title}' 执行失败，请检查日志"
        elif status == "PAUSED":
            fallback_text = f"任务 '{title}' 已暂停"
        elif status == "CANCELLED":
            fallback_text = f"任务 '{title}' 已取消"
        else:
            fallback_text = f"任务 '{title}' 状态: {status}"
        
        # 使用 LLM 增强
        enhanced_text = self._enhance_text_with_llm(
            base_info={
                "title": title,
                "status": status,
                "progress_percent": int(progress * 100),
                "error_summary": error_summary,
                "fallback_text": fallback_text
            },
            context_type="task_status"
        )
        
        # 生成建议操作
        suggested_actions = []
        if status == "RUNNING":
            suggested_actions.append(
                SuggestedActionDTO(
                    type=ActionType.PAUSE,
                    title="暂停任务",
                    payload=f"PAUSE_TASK_{task_id}"
                )
            )
        elif status == "PAUSED":
            suggested_actions.append(
                SuggestedActionDTO(
                    type=ActionType.RESUME,
                    title="恢复任务",
                    payload=f"RESUME_TASK_{task_id}"
                )
            )
        
        suggested_actions.extend([
            SuggestedActionDTO(
                type=ActionType.QUERY,
                title="查看详细日志",
                payload=f"QUERY_TASK_LOGS_{task_id}"
            ),
            SuggestedActionDTO(
                type=ActionType.CANCEL,
                title="取消任务",
                payload=f"CANCEL_TASK_{task_id}"
            )
        ])
        
        # 生成任务状态摘要
        task_status = TaskStatusSummary(
            task_id=task_id,
            status=status,
            progress=progress,
            message=enhanced_text
        )
        
        return self.generate_response(
            session_id=session_id,
            response_text=enhanced_text,
            suggested_actions=suggested_actions,
            task_status=task_status,
            requires_input=False,
            display_data=task_status_info
        )
    
    def generate_fill_slot_response(self, session_id: str, missing_slots: List[str], draft_id: str) -> SystemResponseDTO:
        """生成填槽请求响应
        
        Args:
            session_id: 会话ID
            missing_slots: 缺失的槽位列表
            draft_id: 草稿ID
            
        Returns:
            系统响应DTO
        """
        # 槽位示例值映射
        slot_examples = {
            "task_name": "数据分析报告",
            "target_url": "https://example.com",
            "start_time": "每天上午9点",
            "end_time": "每天下午5点",
            "frequency": "每天一次",
            "max_runs": "10次"
        }
        
        if missing_slots:
            current_slot = missing_slots[0]
            slot_display = self._get_slot_display_name(current_slot)
            example_value = slot_examples.get(current_slot, "相关信息")
            fallback_text = f"请提供 {slot_display}"
            
            # 使用 LLM 增强
            enhanced_text = self._enhance_text_with_llm(
                base_info={
                    "slot_display_name": slot_display, 
                    "example_value": example_value,
                    "fallback_text": fallback_text
                },
                context_type="slot_fill"
            )
            
            # 生成建议操作
            suggested_actions = [
                SuggestedActionDTO(
                    type=ActionType.CANCEL,
                    title="取消任务",
                    payload=f"CANCEL_DRAFT_{draft_id}"
                )
            ]
            
            return self.generate_response(
                session_id=session_id,
                response_text=enhanced_text,
                suggested_actions=suggested_actions,
                requires_input=True,
                awaiting_slot=current_slot
            )
        
        # 如果没有缺失槽位，请求确认
        fallback_text = "请确认任务信息是否正确？"
        # 使用 LLM 增强
        enhanced_text = self._enhance_text_with_llm(
            base_info={"fallback_text": fallback_text},
            context_type="default"
        )
        
        # 生成建议操作
        suggested_actions = [
            SuggestedActionDTO(
                type=ActionType.CONFIRM,
                title="确认执行",
                payload=f"CONFIRM_DRAFT_{draft_id}"
            ),
            SuggestedActionDTO(
                type=ActionType.CANCEL,
                title="取消任务",
                payload=f"CANCEL_DRAFT_{draft_id}"
            ),
            SuggestedActionDTO(
                type=ActionType.MODIFY,
                title="修改信息",
                payload=f"MODIFY_DRAFT_{draft_id}"
            )
        ]
        
        return self.generate_response(
            session_id=session_id,
            response_text=enhanced_text,
            suggested_actions=suggested_actions,
            requires_input=True
        )
    
    def generate_query_response(self, session_id: str, query_result: Dict[str, Any]) -> SystemResponseDTO:
        """生成查询结果响应
        
        Args:
            session_id: 会话ID
            query_result: 查询结果
            
        Returns:
            系统响应DTO
        """
        total = query_result.get("total", 0)
        tasks = query_result.get("tasks", [])
        
        fallback_text = f"找到 {total} 个任务" if total > 0 else "没有找到匹配的任务"
        
        # 使用 LLM 增强
        enhanced_text = self._enhance_text_with_llm(
            base_info={
                "total": total,
                "tasks": tasks,
                "fallback_text": fallback_text
            },
            context_type="query_result"
        )
        
        # 生成建议操作
        suggested_actions = [
            SuggestedActionDTO(
                type=ActionType.QUERY,
                title="查看详情",
                payload=f"QUERY_TASK_DETAIL_{tasks[0]['task_id']}"
            ) if tasks else None
        ]
        
        # 过滤掉None值
        suggested_actions = [action for action in suggested_actions if action]
        
        return self.generate_response(
            session_id=session_id,
            response_text=enhanced_text,
            suggested_actions=suggested_actions,
            requires_input=False,
            display_data=query_result
        )
    
    def generate_error_response(self, session_id: str, error_message: str) -> SystemResponseDTO:
        """生成错误响应
        
        Args:
            session_id: 会话ID
            error_message: 错误信息
            
        Returns:
            系统响应DTO
        """
        fallback_text = f"抱歉，发生了错误：{error_message}"
        
        # 使用 LLM 增强
        enhanced_text = self._enhance_text_with_llm(
            base_info={"error_message": error_message, "fallback_text": fallback_text},
            context_type="error"
        )

        # 生成建议操作
        suggested_actions = [
            SuggestedActionDTO(
                type=ActionType.RETRY,
                title="重试",
                payload="RETRY_OPERATION"
            ),
            SuggestedActionDTO(
                type=ActionType.CANCEL,
                title="取消",
                payload="CANCEL_OPERATION"
            )
        ]

        return self.generate_response(
            session_id=session_id,
            response_text=enhanced_text,
            suggested_actions=suggested_actions,
            requires_input=False
        )
    
    def generate_idle_response(self, session_id: str, idle_message: str) -> SystemResponseDTO:
        """生成闲聊模式响应
        
        Args:
            session_id: 会话ID
            idle_message: 闲聊消息
            
        Returns:
            系统响应DTO
        """
        fallback_text = idle_message
        
        # 使用 LLM 增强
        enhanced_text = self._enhance_text_with_llm(
            base_info={"fallback_text": fallback_text},
            context_type="idle"
        )
        
        return self.generate_response(
            session_id=session_id,
            response_text=enhanced_text,
            requires_input=True
        )
    
    def _enhance_text_with_llm(
        self,
        base_info: Dict[str, Any],
        context_type: str = "default"
    ) -> str:
        """
        使用 LLM 增强响应文本的人性化程度，生成 Markdown 格式输出
        
        Args:
            base_info: 包含原始信息的字典（如 task_title, status, progress 等）
            context_type: 上下文类型，用于定制 prompt（如 "task_status", "error", "slot_fill"）
        
        Returns:
            增强后的 Markdown 格式响应文本
        """
        if not self.llm:
            # 若未初始化 LLM，回退到原始文本
            return base_info.get("fallback_text", "系统消息")

        # 根据 context_type 构造 prompt
        prompts = {
            "task_creation": (
                "你是一个温暖、专业的任务助手。请根据以下信息，生成 Markdown 格式的任务创建成功响应。\n"
                "要求：\n"
                "- 开头使用 🎉 表情符号\n"
                "- 任务名称用 **加粗** 突出显示\n"
                "- 任务 ID 用 `代码格式` 展示\n"
                "- 语气要像朋友一样亲切，避免机械感\n"
                "- 包含一句后续操作的引导语\n"
                "- 只输出 Markdown 内容，不要添加任何解释\n\n"
                f"任务标题：{base_info['title']}\n"
                f"任务ID：{base_info['task_id']}\n"
            ),
            "task_status": (
                "你是一个温暖、专业的任务助手。请根据以下信息，生成 Markdown 格式的任务状态响应。\n"
                "要求：\n"
                "- 使用合适的表情符号开头（成功→✨，运行中→⏳，失败→😟，暂停→⏸️，取消→❌）\n"
                "- 任务名称用 **加粗** 突出显示\n"
                "- 进度百分比用 **加粗** 展示\n"
                "- 语气要亲切、有温度，根据状态调整情绪（成功时鼓励，失败时共情，等待时安抚）\n"
                "- 加入适当的空行创造呼吸感\n"
                "- 只输出 Markdown 内容，不要添加任何解释\n\n"
                f"任务标题：{base_info['title']}\n"
                f"状态：{base_info['status']}\n"
                f"进度百分比：{base_info.get('progress_percent', 0)}\n"
                f"错误摘要（如有）：{base_info.get('error_summary', '')}\n"
            ),
            "error": (
                "你是一位体贴的客服助手。请根据以下错误信息，生成 Markdown 格式的友好提示。\n"
                "要求：\n"
                "- 开头使用 ⚠️ 或 😟 表情符号\n"
                "- 错误信息用 > 引用块包裹\n"
                "- 提供 1~2 条行动建议，用 - 列表展示\n"
                "- 结尾给予鼓励和支持\n"
                "- 语气亲切，避免推卸责任\n"
                "- 加入适当的空行创造呼吸感\n"
                "- 只输出 Markdown 内容，不要添加任何解释\n\n"
                f"原始错误：{base_info['error_message']}\n"
            ),
            "slot_fill": (
                "你是一位耐心的引导者。请根据以下信息，生成 Markdown 格式的填槽请求响应。\n"
                "要求：\n"
                "- 开头使用 📝 表情符号\n"
                "- 缺失的字段名称用 **加粗** 突出显示\n"
                "- 给出简单的示例（用括号包裹，如 `(例如：每天上午9点)`）\n"
                "- 语气轻松、亲切，带有鼓励\n"
                "- 只输出 Markdown 内容，不要添加任何解释\n\n"
                f"缺失字段显示名：{base_info['slot_display_name']}\n"
                f"示例值：{base_info.get('example_value', '相关信息')}\n"
            ),
            "confirm_draft": (
                "你是一位专业的任务助手。请根据以下草稿信息，生成 Markdown 格式的确认请求响应。\n"
                "要求：\n"
                "- 开头使用 🔍 表情符号\n"
                "- 用 - 列表展示关键任务信息\n"
                "- 适当突出重要信息\n"
                "- 结尾引导用户点击确认按钮\n"
                "- 语气亲切，充满信任感\n"
                "- 加入适当的空行创造呼吸感\n"
                "- 只输出 Markdown 内容，不要添加任何解释\n\n"
                f"草稿信息：{base_info['draft_info']}\n"
            ),
            "query_result": (
                "你是一个友好的查询助手。请根据以下查询结果，生成 Markdown 格式的响应。\n"
                "要求：\n"
                "- 开头使用合适的表情符号（有结果→📊，无结果→🕳️）\n"
                "- 总任务数用 **加粗** 突出显示\n"
                "- 如果有任务，列出最近一个任务的标题（**加粗**）、ID（`代码格式`）和状态\n"
                "- 状态表情符号映射：RUNNING→⏳, COMPLETED→✅, FAILED→❌, PAUSED→⏸️, CANCELLED→❌\n"
                "- 语气亲切，带有引导性\n"
                "- 加入适当的空行创造呼吸感\n"
                "- 只输出 Markdown 内容，不要添加任何解释\n\n"
                f"总任务数：{base_info['total']}\n"
                f"任务列表（字典列表）：{base_info.get('tasks', [])}\n"
            ),
            "idle": (
                "你是一个友好的聊天助手。请将以下空闲消息改写成一句自然、流畅、友好的 Markdown 格式回复。\n"
                "要求：\n"
                "- 加入合适的表情符号\n"
                "- 语气亲切，像朋友一样\n"
                "- 只输出 Markdown 内容，不要添加任何解释\n\n"
                f"原始消息：{base_info['fallback_text']}\n"
            ),
            "default": (
                "请将以下系统消息改写成一句自然、流畅、对用户友好的 Markdown 格式文本。\n"
                "要求：\n"
                "- 加入合适的表情符号\n"
                "- 突出关键信息\n"
                "- 语气亲切，避免机械感\n"
                "- 只输出 Markdown 内容，不要添加任何解释\n\n"
                f"原始消息：{base_info['fallback_text']}\n"
            )
        }

        prompt = prompts.get(context_type, prompts["default"])
        
        try:
            enhanced = self.llm.generate(prompt, max_tokens=120, temperature=0.6)
            # 清理多余引号或解释
            text = enhanced.strip()
            if text.startswith(('"', "'", "\"")) and text.endswith(('"', "'", "\"")):
                text = text[1:-1]
            return text
        except Exception as e:
            # LLM 调用失败时回退
            return base_info.get("fallback_text", "系统消息")
    
    def _get_slot_display_name(self, slot_name: str) -> str:
        """获取槽位的显示名称
        
        Args:
            slot_name: 槽位名称
            
        Returns:
            槽位的显示名称
        """
        # 槽位名称映射，实际应该从配置或数据库中获取
        slot_display_names = {
            "task_name": "任务名称",
            "target_url": "目标网址",
            "start_time": "开始时间",
            "end_time": "结束时间",
            "frequency": "执行频率",
            "max_runs": "最大执行次数"
        }
        
        return slot_display_names.get(slot_name, slot_name)