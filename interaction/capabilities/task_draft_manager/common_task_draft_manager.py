from typing import Dict, Any, Optional, List
import json
from .interface import ITaskDraftManagerCapability
from common import (
    TaskDraftDTO,
    SlotValueDTO,
    ScheduleDTO,
    SlotSource,
    IntentRecognitionResultDTO,
    TaskDraftStatus
)
from external.database.task_draft_repo import TaskDraftRepository
from ..llm.interface import ILLMCapability
from ..registry import capability_registry
from ..memory.interface import IMemoryCapability

class CommonTaskDraft(ITaskDraftManagerCapability):
    """任务草稿管理器 - 维护未完成的任务草稿，管理多轮填槽过程"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务草稿管理器"""
        self.logger.info("初始化任务草稿管理器")
        self.config = config
        self._llm = None
        # 初始化 storage
        
            # 如果没有提供storage，创建一个默认的TaskDraftRepository实例
        self.draft_storage = TaskDraftRepository()
        self.logger.info("任务草稿管理器初始化完成")
        
    @property
    def llm(self) -> ILLMCapability:
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
    
    def shutdown(self) -> None:
        """关闭任务草稿管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "task_draft"
    
    def create_draft(self, task_type: str, session_id: str, user_id: str) -> TaskDraftDTO:
        """创建新的任务草稿
        
        Args:
            task_type: 任务类型
            session_id: 会话ID
            user_id: 用户ID
            
        Returns:
            任务草稿DTO
        """
        self.logger.info(f"创建任务草稿，task_type={task_type}, session_id={session_id}, user_id={user_id}")
        draft = TaskDraftDTO(
            user_id=user_id,
            task_type=task_type,
            status=TaskDraftStatus.FILLING,
            slots={},
            missing_slots=[],
            invalid_slots=[],
            schedule=None,
            is_cancelable=True,
            is_resumable=True,
            original_utterances=[],
        )
        
        # 保存到存储
        self.draft_storage.save_draft(draft)
        self.logger.info(f"任务草稿创建成功，draft_id={draft.draft_id}")
        return draft
    
    def submit_draft(self, draft: TaskDraftDTO) -> TaskDraftDTO:
        """提交草稿，执行提交前校验
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            提交后的任务草稿
        """
        self.logger.info(f"提交任务草稿，draft_id={draft.draft_id}, task_type={draft.task_type}")
        # 1. 执行必填项校验
        self._validate_required_slots(draft)
        # 2. 更新状态
        draft.status = TaskDraftStatus.SUBMITTED
        # 3. 保存到数据库
        self.draft_storage.save_draft(draft)
        self.logger.info(f"任务草稿提交成功，draft_id={draft.draft_id}")
        return draft
    
    def cancel_draft(self, draft: TaskDraftDTO) -> TaskDraftDTO:
        """取消草稿
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            取消后的任务草稿
        """
        self.logger.info(f"取消任务草稿，draft_id={draft.draft_id}, task_type={draft.task_type}")
        draft.status = TaskDraftStatus.CANCELLED
        self.draft_storage.save_draft(draft)
        self.logger.info(f"任务草稿取消成功，draft_id={draft.draft_id}")
        return draft
    
    def set_draft_pending_confirm(self, draft: TaskDraftDTO) -> TaskDraftDTO:
        """将草稿设置为待确认状态
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            更新后的任务草稿
        """
        draft.status = TaskDraftStatus.PENDING_CONFIRM
        self.draft_storage.save_draft(draft)
        return draft
    
    def _validate_required_slots(self, draft: TaskDraftDTO) -> None:
        """校验必填项，抛出异常如果不满足
        
        Args:
            draft: 任务草稿DTO
            
        Raises:
            ValueError: 如果必填项不满足
        """
        # 调用现有的validate_draft方法进行校验
        validated_draft = self.validate_draft(draft)
        if validated_draft.missing_slots or validated_draft.invalid_slots:
            error_msg = """
            任务草稿不满足提交条件：
            缺失必填项：{}
            无效项：{}
            """.format(
                ", ".join(validated_draft.missing_slots),
                ", ".join(validated_draft.invalid_slots)
            )
            self.logger.error(f"任务草稿校验失败，draft_id={draft.draft_id}, {error_msg.strip()}")
            raise ValueError(error_msg.strip())
    
    def update_draft(self, draft: TaskDraftDTO) -> bool:
        """更新任务草稿
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            是否更新成功
        """
        return self.draft_storage.save_draft(draft)
    
    def get_draft(self, draft_id: str) -> Optional[TaskDraftDTO]:
        """获取任务草稿
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            任务草稿DTO，不存在返回None
        """
        self.logger.info(f"获取任务草稿，draft_id={draft_id}")
        draft = self.draft_storage.get_draft(draft_id)
        if draft:
            self.logger.info(f"获取任务草稿成功，draft_id={draft_id}, task_type={draft.task_type}")
        else:
            self.logger.info(f"任务草稿不存在，draft_id={draft_id}")
        return draft
    
    def delete_draft(self, draft_id: str) -> bool:
        """删除任务草稿
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            是否删除成功
        """
        self.logger.info(f"删除任务草稿，draft_id={draft_id}")
        result = self.draft_storage.delete_draft(draft_id)
        self.logger.info(f"删除任务草稿{'成功' if result else '失败'}，draft_id={draft_id}")
        return result
    
    def add_utterance_to_draft(self, draft: TaskDraftDTO, utterance: str) -> TaskDraftDTO:
        """添加用户输入到草稿历史（仅修改内存对象，需手动调用 update_draft 持久化）
        
        Args:
            draft: 任务草稿DTO
            utterance: 用户输入
            
        Returns:
            更新后的任务草稿
        """
        if utterance not in draft.original_utterances:
            draft.original_utterances.append(utterance)
        return draft
    
    def update_slot(self, draft: TaskDraftDTO, slot_name: str, slot_value: SlotValueDTO) -> TaskDraftDTO:
        """更新草稿的槽位值
        
        Args:
            draft: 任务草稿DTO
            slot_name: 槽位名称
            slot_value: 槽位值DTO
            
        Returns:
            更新后的任务草稿
        """
        draft.slots[slot_name] = slot_value
        return draft
    
    def fill_entity_to_slot(self, draft: TaskDraftDTO, entity_name: str, entity_value: Any, source: SlotSource) -> TaskDraftDTO:
        """将实体填充到对应的槽位
        
        Args:
            draft: 任务草稿DTO
            entity_name: 实体名称
            entity_value: 实体值
            source: 槽位来源
            
        Returns:
            更新后的任务草稿
        """
        # 这里假设实体名称与槽位名称一致，实际可能需要映射
        slot_value = SlotValueDTO(
            raw=str(entity_value),
            resolved=entity_value,
            confirmed=False,
            source=source
        )
        return self.update_slot(draft, entity_name, slot_value)
    
    def _is_slot_value_valid(self, slot_name: str, slot_value: Any, schema: Dict[str, Any]) -> bool:
        """验证槽位值是否符合格式要求
        
        Args:
            slot_name: 槽位名称
            slot_value: 槽位值
            schema: 任务类型的schema
            
        Returns:
            是否有效
        """
        slot_types = schema.get("slot_types", {})
        slot_type = slot_types.get(slot_name)
        
        if slot_type is None:
            return True
        
        if slot_type == "datetime":
            # 简单的日期时间格式检查
            return isinstance(slot_value, str) or isinstance(slot_value, int)
        elif slot_type == "int":
            return isinstance(slot_value, int)
        elif slot_type == "email":
            # 简单的邮箱格式检查
            return isinstance(slot_value, str) and "@" in slot_value
        
        return True
    
    def validate_draft(self, draft: TaskDraftDTO) -> TaskDraftDTO:
        """验证任务草稿，检查必填槽位和格式
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            更新后的任务草稿，包含缺失和无效的槽位
        """
        self.logger.debug(f"验证任务草稿，draft_id={draft.draft_id}, task_type={draft.task_type}")
        schema = self.config.get("task_schemas", {}).get(draft.task_type, {})
        required_slots = schema.get("required_slots", [])
        
        missing = []
        invalid = []

        for slot_name in required_slots:
            slot = draft.slots.get(slot_name)
            if slot is None or not slot.confirmed:
                missing.append(slot_name)
            else:
                # 增加格式校验（如时间、邮箱等）
                if not self._is_slot_value_valid(slot_name, slot.resolved, schema):
                    invalid.append(slot_name)

        draft.missing_slots = missing
        draft.invalid_slots = invalid
        self.logger.debug(f"任务草稿验证完成，draft_id={draft.draft_id}, missing_slots={missing}, invalid_slots={invalid}")
        return draft
    
    def prepare_for_execution(self, draft: TaskDraftDTO) -> Dict[str, Any]:
        """准备任务执行所需的所有参数
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            执行参数字典
        """
        parameters = {}
        for slot_name, slot_value in draft.slots.items():
            if slot_value.confirmed:  # 关键：只取已确认的
                parameters[slot_name] = slot_value.resolved
        # 确保 description 字段存在：从 original_utterances 构建任务的自然语言描述
        if "description" not in parameters and draft.original_utterances:
            # 过滤掉系统补充信息，只保留用户原始输入
            user_utterances = [
                u for u in draft.original_utterances
            ]
            if user_utterances:
                parameters["description"] = " ".join(user_utterances)
        return parameters
    
    def set_schedule(self, draft: TaskDraftDTO, schedule: ScheduleDTO) -> TaskDraftDTO:
        """设置任务的调度信息
        
        Args:
            draft: 任务草稿DTO
            schedule: 调度信息DTO
            
        Returns:
            更新后的任务草稿
        """
        draft.schedule = schedule
        return draft
    
    def confirm_slot(self, draft: TaskDraftDTO, slot_name: str) -> TaskDraftDTO:
        """确认某个槽位的值
        
        Args:
            draft: 任务草稿DTO
            slot_name: 槽位名称
            
        Returns:
            更新后的任务草稿
        """
        if slot_name in draft.slots:
            draft.slots[slot_name].confirmed = True
        return draft
    
    def confirm_all_slots(self, draft: TaskDraftDTO) -> TaskDraftDTO:
        """确认所有槽位的值
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            更新后的任务草稿
        """
        for slot in draft.slots.values():
            slot.confirmed = True
        return draft
    
    def generate_missing_slot_prompt(self, draft: TaskDraftDTO) -> str:
        """使用LLM生成针对缺失槽位的自然语言追问
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            生成的自然语言追问
        """
        task_type = draft.task_type
        missing = draft.missing_slots
        history = "\n".join(draft.original_utterances[-3:])  # 最近3轮对话

        prompt = f"""
你是一个任务助理，正在帮助用户完成一个「{task_type}」任务。
用户已经提供了以下信息：
{history}

但还缺少以下信息：{', '.join(missing)}
请用一句简洁、友好的中文问句，引导用户补充**其中一个最关键或最易回答**的缺失信息。
不要一次问多个问题，只问一个。
直接输出问句，不要解释。
        """.strip()

        response = self.llm.generate(prompt, max_tokens=50, temperature=0.3)
        return response.strip()
    
    def clarify_slot_value(self, draft: TaskDraftDTO, slot_name: str) -> str:
        """使用LLM生成针对特定槽位的澄清问题
        
        Args:
            draft: 任务草稿DTO
            slot_name: 槽位名称
            
        Returns:
            生成的澄清问句
        """
        slot = draft.slots[slot_name]
        prompt = f"""
用户输入："{slot.raw}"，系统解析为："{slot.resolved}"。
但这可能存在歧义或不完整。
请用一句自然的中文，礼貌地请用户确认或澄清这个信息。
例如："您说的‘下午’是指14点到18点之间吗？"
直接输出问句。
        """
        return self.llm.generate(prompt, max_tokens=60).strip()
    
    def _sanitize_json(self, json_str: str) -> str:
        """清理LLM返回的JSON字符串，移除可能的markdown包裹
        
        Args:
            json_str: LLM返回的字符串
            
        Returns:
            清理后的JSON字符串
        """
        if not json_str:
            return json_str

        # 先去除首尾空白
        json_str = json_str.strip()
        # 移除可能的markdown代码块
        if json_str.startswith('```json'):
            json_str = json_str[7:]
        if json_str.startswith('```'):
            json_str = json_str[3:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]
        return json_str.strip()
    
    def extract_slots_with_llm(self, task_type: str, utterance: str, current_slots: Dict[str, Any]) -> Dict[str, Any]:
        """当NLU结果较弱时，使用LLM联合推理意图和槽位
        
        Args:
            task_type: 任务类型
            utterance: 用户最新输入
            current_slots: 当前已知的槽位信息
            
        Returns:
            从用户输入中提取的槽位
        """
        schema = self.config.get("task_schemas", {}).get(task_type, {})
        required = schema.get("required_slots", [])
        optional = schema.get("optional_slots", [])

        prompt = f"""
任务类型：{task_type}
用户最新输入："{utterance}"
当前已知信息：{current_slots}

请从用户输入中提取以下可能的槽位值（仅返回JSON，不要解释）：
- 必填槽位：{required}
- 可选槽位：{optional}

输出格式：{{"槽位名": "值"}}
如果无法确定，跳过该槽位。
        """

        try:
            json_str = self.llm.generate(prompt, max_tokens=150, temperature=0.0)
            sanitized = self._sanitize_json(json_str)
            return json.loads(sanitized)
        except Exception as e:
            return {}
    
    def generate_confirmation_summary(self, draft: TaskDraftDTO) -> str:
        """使用LLM生成任务草稿的确认摘要
        
        Args:
            draft: 任务草稿DTO
            
        Returns:
            生成的确认摘要
        """
        params = {k: v.resolved for k, v in draft.slots.items() if v.confirmed}
        prompt = f"""
你是一个助理，正在帮用户确认一个「{draft.task_type}」任务。
已确认的信息如下：
{json.dumps(params, ensure_ascii=False, indent=2)}

请用一段简洁、清晰的中文总结这个任务，并以“请确认是否正确？”结尾。
        """
        return self.llm.generate(prompt, max_tokens=100).strip()
    
    def update_draft_from_intent(self, draft: TaskDraftDTO, intent_result: IntentRecognitionResultDTO) -> Dict[str, Any]:
        """
        [修改后] 根据意图更新草稿，并动态生成下一步回复
        适应场景：无固定Schema，依靠LLM动态判断缺什么参数
        
        核心流程：
        1. 实体填充：将识别到的实体填入槽位（不要使用NLU，直接使用llm进行实体填充）
        2. 动态评估：调用LLM评估完整性
        3. 更新状态：根据评估结果更新draft状态
        4. 生成回复：根据状态生成合适的回复文本
        """
        self.logger.info(f"根据意图更新草稿，draft_id={draft.draft_id}, intent={intent_result.intent}")
        # 0. 获取用户原始输入并保存到草稿历史中
        original_utterance = intent_result.raw_nlu_output.get("enhanced_utterance", "")
        if original_utterance:
            self.add_utterance_to_draft(draft, original_utterance)
        
        # 1. 把识别到的实体（Entities）全部填入槽位（Slots）
        # 既然槽位是虚的，我们就直接把 entity.name 当作 slot_name 存进去
        if intent_result.entities:
            for entity in intent_result.entities:
                # SlotSource.INFERENCE 表示这是从推理中获取的
                self.fill_entity_to_slot(
                    draft, 
                    entity.name, 
                    entity.resolved_value or entity.value, 
                    SlotSource.INFERENCE
                )
        
        # 2. 持久化保存一下当前的草稿状态
        self.update_draft(draft)
        
        # 3. [关键] 调用 LLM 动态评估当前草稿的完整性
        ##TODO：这里填槽前查询已知信息（放在event里）
        original_utterance = intent_result.raw_nlu_output.get("original_utterance", "")
        evaluation_result = self._evaluate_draft_completeness(draft, original_utterance)
        
        # 4. 根据评估结果更新Draft状态
        is_ready = evaluation_result["is_ready"]
        
        # 如果还需要补充信息，进入循环尝试从memory中获取
        if not is_ready:
            try:
                # 获取memory能力
                memory_cap = capability_registry.get_capability("memory", IMemoryCapability)
                
                # 循环获取memory信息，直到无法获取新信息或完全就绪
                while not is_ready:
                    # 记录当前缺失的槽位数量
                    current_missing_slots = evaluation_result.get("missing_slot", "unknown")
                    
                    # 从evaluation_result中获取缺失的信息描述
                    missing_info = evaluation_result["analysis"]
                    
                    # 查询memory
                    # 注意：这里需要user_id，暂时从draft中获取，如果没有则使用默认值
                    user_id = getattr(draft, "user_id", "default_user")
                    memory_result = memory_cap.search_memories(user_id, missing_info, limit=3)
                    
                    # 如果memory中没有相关信息，跳出循环
                    if not memory_result:
                        break
                    
                    # 将memory结果添加到draft的原始 utterances 中，以便后续评估使用
                    draft = self.add_utterance_to_draft(draft, f"[系统补充信息] {memory_result}")
                    
                    # 重新评估草稿完整性
                    evaluation_result = self._evaluate_draft_completeness(draft, original_utterance)
                    new_is_ready = evaluation_result["is_ready"]
                    new_missing_slots = evaluation_result.get("missing_slot", "unknown")
                    
                    # 更新is_ready状态
                    is_ready = new_is_ready
                    
                    # 如果已经完全就绪，跳出循环
                    if is_ready:
                        break
                    
                    # 如果没有新填好的空（缺失的槽位没有变化），跳出循环
                    if current_missing_slots == new_missing_slots:
                        break
            except Exception as e:
                self.logger.exception(f"从memory获取信息失败")
                # 如果获取memory失败，继续使用原来的评估结果
        
        if is_ready:
            # 如果LLM认为信息足够，设置为待确认状态
            draft.status = TaskDraftStatus.PENDING_CONFIRM
            draft.completeness_score = 1.0
            draft.next_clarification_question = None
        else:
            # 如果还需要更多信息，保持填槽状态
            draft.status = TaskDraftStatus.FILLING
            draft.completeness_score = 0.5  # 可以根据LLM的分析调整
            draft.next_clarification_question = evaluation_result["response_to_user"]
        
        # 5. 更新草稿
        self.update_draft(draft)
        
        # 6. 返回 InteractionHandler 能够理解的字典格式
        result = {
            "task_draft": draft,
            "response_text": evaluation_result["response_to_user"],  # 直接发给用户的回复
            "requires_input": not is_ready,  # 如果还没决定执行，就继续等待用户输入
            "should_execute": is_ready       # 如果 LLM 觉得信息够了，可以设为 True
        }
        self.logger.info(f"根据意图更新草稿完成，draft_id={draft.draft_id}, is_ready={is_ready}")
        return result

    def _evaluate_draft_completeness(self, draft: TaskDraftDTO, last_user_utterance: str) -> Dict[str, Any]:
        """
        使用LLM评估当前任务草稿的完整性
        核心功能：
        - 调用LLM分析当前收集的参数
        - 判断是否满足最小必要条件
        - 生成追问或确认摘要
        
        Args:
            draft: 当前任务草稿
            last_user_utterance: 用户最新输入
            
        Returns:
            评估结果，包含is_ready、missing_slot、analysis、response_to_user
        """
        # 提取当前已有的所有参数（kv对）
        current_slots = {k: v.resolved for k, v in draft.slots.items()}
        current_slots_str = json.dumps(current_slots, ensure_ascii=False, indent=2)
        
        # 最近对话历史
        dialog_history = "\n".join(draft.original_utterances[-5:])  # 最近5轮对话
        
        # 参考prompt：
        prompt = f"""
        你是一个专业的任务分析师。用户想要执行一个「{draft.task_type}」任务。

        【已收集的参数】
        {current_slots_str}

        【最近对话历史】
        {dialog_history}

        【你的判断逻辑】
        1. 这是一个开放式任务。请判断当前收集的参数是否满足了任务执行的**最小必要条件**。
        2. 不要过度索取细节。如果核心意图明确，且关键参数（如对象、内容、时间等）已有，即可认为就绪。
        3. 如果就绪：请生成一段"确认摘要"，并询问用户是否确认。
        4. 如果**不**就绪：请找出**当前最缺失的一个**关键参数，并生成一句自然的追问。

        【输出格式(JSON)】
        {{
            "is_ready": boolean,  // true 表示可以执行/待确认，false 表示还需要参数
            "missing_slot": "string or null", // 如果 false，指出缺什么
            "analysis": "string", // 简短的分析理由
            "response_to_user": "string" // 直接发给用户的回复（追问或确认请求）
        }}
        """
        
        try:
            # 调用LLM生成评估结果
            response = self.llm.generate(prompt, max_tokens=200, temperature=0.3)
            
            # 清理并解析JSON结果
            sanitized_json = self._sanitize_json(response)
            evaluation_result = json.loads(sanitized_json)
            
            # 验证必要字段
            if not all(key in evaluation_result for key in ["is_ready", "missing_slot", "analysis", "response_to_user"]):
                raise ValueError("LLM返回的评估结果缺少必要字段")
            
            return evaluation_result
        except Exception as e:
            # LLM调用失败时的兜底逻辑
            self.logger.exception(f"_evaluate_draft_completeness failed")
            return {
                "is_ready": False,
                "missing_slot": "unknown",
                "analysis": "系统暂时无法评估任务完整性",
                "response_to_user": "抱歉，我刚刚走神了，没听清您的要求，能麻烦您再详细描述一遍任务吗？"
            }
    
    def _generate_dynamic_response(self, draft: TaskDraftDTO, last_user_utterance: str) -> tuple[str, bool]:
        """
        动态决策助手 - 已整合到_evaluate_draft_completeness方法中
        保留此方法以保持向后兼容
        """
        evaluation_result = self._evaluate_draft_completeness(draft, last_user_utterance)
        return evaluation_result["response_to_user"], evaluation_result["is_ready"]