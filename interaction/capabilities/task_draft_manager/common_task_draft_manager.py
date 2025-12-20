from typing import Dict, Any, Optional, List
import json
from .interface import ITaskDraftManagerCapability
from ...common import (
    TaskDraftDTO,
    SlotValueDTO,
    ScheduleDTO,
    SlotSource,
    IntentRecognitionResultDTO
)
from ...external.database.task_draft_repo import TaskDraftRepository
from ..llm.interface import ILLMCapability

class CommonTaskDraft(ITaskDraftManagerCapability):
    """任务草稿管理器 - 维护未完成的任务草稿，管理多轮填槽过程"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务草稿管理器"""
        self.config = config
        self._llm = None
        # 初始化 storage
        
            # 如果没有提供storage，创建一个默认的TaskDraftRepository实例
        self.draft_storage = TaskDraftRepository()
        
    @property
    def llm(self):
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
        draft = TaskDraftDTO(
            task_type=task_type,
            status="DRAFT",
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
        return draft
    
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
        return self.draft_storage.get_draft(draft_id)
    
    def delete_draft(self, draft_id: str) -> bool:
        """删除任务草稿
        
        Args:
            draft_id: 草稿ID
            
        Returns:
            是否删除成功
        """
        return self.draft_storage.delete_draft(draft_id)
    
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
    
    def update_draft_from_intent(self, draft: TaskDraftDTO, intent_result: IntentRecognitionResultDTO) -> TaskDraftDTO:
        """根据意图识别结果更新任务草稿
        
        Args:
            draft: 任务草稿DTO
            intent_result: 意图识别结果DTO
            
        Returns:
            更新后的任务草稿
        """
        # 将识别到的实体填充到槽位
        for entity in intent_result.entities:
            draft = self.fill_entity_to_slot(
                draft, entity.name, entity.resolved_value or entity.value, SlotSource.INFERENCE)
        return draft