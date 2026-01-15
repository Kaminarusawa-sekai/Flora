import json
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter

from .interface import IIntentRecognitionManagerCapability
from ..llm.interface import ILLMCapability
from common import (
    IntentRecognitionResultDTO,
    IntentType,
    EntityDTO,
    UserInputDTO,
    DialogStateDTO
)

# 枚举值映射
INTENT_NAME_TO_ENUM = {intent.value: intent for intent in IntentType}
ALLOWED_INTENT_NAMES = list(INTENT_NAME_TO_ENUM.keys())

class CommonIntentRecognition(IIntentRecognitionManagerCapability):
    """增强版意图识别：输出主意图 + 候选意图 + 实体 + 歧义标记"""

    def __init__(self):
        super().__init__()
        self.config = None
        self._llm = None
        self.ambiguity_threshold = 0.2

    def initialize(self, config: Dict[str, Any]) -> None:
        self.logger.info("初始化意图识别管理器")
        self.config = config
        self.ambiguity_threshold = config.get("ambiguity_threshold", 0.2)  # top1 - top2 < 此值则视为歧义
        self.logger.info(f"意图识别管理器初始化完成，歧义阈值: {self.ambiguity_threshold}")
        
    @property
    def llm(self)-> ILLMCapability:
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
    
    def shutdown(self) -> None:
        self.logger.info("关闭意图识别管理器")
        pass
    
    def get_capability_type(self) -> str:
        self.logger.info("获取能力类型")
        result = "nlu"
        self.logger.info(f"成功获取能力类型，类型={result}")
        return result
    
    def recognize_intent(self, user_input: UserInputDTO) -> IntentRecognitionResultDTO:
        self.logger.info(f"开始意图识别，user_id={user_input.user_id}, session_id={user_input.session_id}")
        utterance = user_input.utterance.strip()
        if not utterance:
            self.logger.info("用户输入为空，返回IDLE_CHAT意图")
            return self._build_result(
                primary=IntentType.IDLE_CHAT,
                confidence=1.0,
                alternatives=[],
                entities=[],
                utterance=utterance,
                raw={}
            )
        
        from ..dialog_state_manager.interface import IDialogStateManagerCapability
        from .. import get_capability
        dialog_state_manager :IDialogStateManagerCapability= get_capability("dialog_state", expected_type=IDialogStateManagerCapability)
        recent_status = dialog_state_manager.get_or_create_dialog_state(user_input.session_id, user_input.user_id)
        # --- 核心修改：将对象转为自然语言描述 ---
        context_desc = self._format_context_for_llm(recent_status)
        # === 阶段1：是否任务相关？===
        stage1_prompt = (
            f"你是一个意图分类助手。请判断用户输入是否与任务管理相关。\n"
            f"任务管理包括：创建任务、补充参数、修改信息、查询状态、取消/暂停/恢复任务。\n\n"
            f"【当前上下文状态】\n{context_desc}\n\n"
            f"【判断规则】\n"
            f"1. 如果当前处于'填槽'或'澄清'状态，用户的简短回答（如'明天'、'张三'、'是的'）应被视为 TASK（用于补充信息）。\n"
            f"2. 只有与当前任务完全无关的闲聊（如'你吃饭了吗'）才判为 IDLE。\n\n"
            f"用户输入：{utterance}\n\n"
            f"请严格按照以下 JSON 格式回复，不要包含任何其他内容：\n"
            f"{{\"intent\": \"TASK\" 或 \"IDLE\", \"reason\": \"简要说明判断依据\"}}"
        )
        try:
            stage1_response:dict = self.llm.generate(stage1_prompt, parse_json=True)
            self.logger.info(f"Stage1 LLM Response: {str(stage1_response)}")
            stage1_result = stage1_response.get("intent", "TASK")
            
        except Exception as e:
            self.logger.exception("Stage1 LLM failed")
            stage1_result = "TASK"

        if "TASK" not in stage1_result: # 宽松匹配
            self.logger.info(f"Stage1判断为非任务相关，返回IDLE_CHAT意图，stage1_result={stage1_result}")
            return self._build_result(
                primary=IntentType.IDLE_CHAT,
                confidence=0.95,
                alternatives=[],
                entities=[],
                utterance=utterance,
                raw={"stage1": stage1_result}
            )

        # === 阶段2：获取意图分布（可要求 LLM 返回多个候选）===
        allowed_str = ", ".join(ALLOWED_INTENT_NAMES)
        stage2_prompt = (
            f"分析用户输入，返回最可能的意图及其置信度。\n\n"
            f"用户输入：{utterance}\n\n"
            f"意图必须从以下选项中选择：{allowed_str}\n"
            f"之前的判断是：{stage1_result}\n"
            f"最近任务状态：{context_desc}\n\n"
            f"请以 JSON 格式返回，包含：\n"
            f"- primary_intent: 字符串\n"
            f"- confidence: 浮点数（0~1）\n"
            f"- alternative_intents: 列表，每个元素为 {{\"intent\": \"...\", \"score\": 0.x}}\n"
            f"- entities: 列表，每个含 name, value, resolved_value\n"
            f"不要输出任何其他内容。"
        )

        llm_raw = ""
        try:
            llm_raw = self.llm.generate(stage2_prompt)
            parsed = json.loads(llm_raw)

            primary_str = parsed.get("primary_intent")
            if primary_str not in INTENT_NAME_TO_ENUM:
                raise ValueError(f"Invalid primary intent: {primary_str}")

            primary = INTENT_NAME_TO_ENUM[primary_str]
            confidence = float(parsed.get("confidence", 0.7))

            # 解析候选意图
            alternatives = []
            for alt in parsed.get("alternative_intents", []):
                intent_str = alt.get("intent")
                score = float(alt.get("score", 0.0))
                if intent_str in INTENT_NAME_TO_ENUM:
                    alternatives.append((INTENT_NAME_TO_ENUM[intent_str], score))

            entities = self._parse_entities_from_llm(parsed.get("entities", []))
            is_ambiguous = self._check_ambiguity(confidence, alternatives)

            self.logger.info(f"成功识别意图，primary={primary}, confidence={confidence:.2f}, is_ambiguous={is_ambiguous}")
            return self._build_result(
                primary=primary,
                confidence=confidence,
                alternatives=alternatives,
                entities=entities,
                utterance=utterance,
                raw={"stage1": stage1_result, "stage2_raw": llm_raw},
                is_ambiguous=is_ambiguous
            )

        except Exception as e:
            self.logger.exception("LLM parsing failed, falling back to rule-based")
            return self._fallback_to_rule_based(utterance, llm_raw)

    def _fallback_to_rule_based(self, utterance: str, llm_raw: str = "") -> IntentRecognitionResultDTO:
        # 规则只能给出主意图，候选为空
        primary, confidence = self._rule_based_intent(utterance)
        entities = self._extract_entities(utterance)
        return self._build_result(
            primary=primary,
            confidence=confidence,
            alternatives=[],
            entities=entities,
            utterance=utterance,
            raw={"fallback": True, "llm_raw_on_failure": llm_raw}
        )

    def _rule_based_intent(self, utterance: str) -> Tuple[IntentType, float]:
        lower_utterance = utterance.lower()
        rules = [
            (["创建", "新建", "添加"], IntentType.CREATE_TASK, 0.9),
            (["修改", "编辑", "更新"], IntentType.MODIFY_TASK, 0.8),
            (["查询", "查看", "列表", "有哪些"], IntentType.QUERY_TASK, 0.9),
            (["删除"], IntentType.DELETE_TASK, 0.8),
            (["取消"], IntentType.CANCEL_TASK, 0.8),
            (["恢复", "继续"], IntentType.RESUME_TASK, 0.7),  # 默认是继续任务
            (["中断", "挂起"], IntentType.PAUSE_TASK, 0.7),
            (["重试"], IntentType.RETRY_TASK, 0.8),
            (["定时", "每天", "每周", "每小时", "计划"], IntentType.SET_SCHEDULE, 0.8),
        ]
        for keywords, intent, conf in rules:
            if any(kw in lower_utterance for kw in keywords):
                # 特殊处理“恢复中断”
                if intent == IntentType.RESUME_TASK and "中断" in lower_utterance:
                    return IntentType.RESUME_TASK, conf
                    
                return intent, conf
        result = IntentType.IDLE_CHAT, 0.6
        self.logger.debug(f"规则匹配结果：intent={result[0]}, confidence={result[1]}")
        return result

    def _extract_entities(self, utterance: str) -> List[EntityDTO]:
        """增强版实体提取:优先 LLM，失败则规则（此处简化为仅 LLM）"""
        prompt = (
            f"从以下用户输入中提取结构化实体信息。\n\n"
            f"用户输入：{utterance}\n\n"
            f"返回 JSON 列表，每个实体包含：name（如 task_name, due_date, priority）, "
            f"value（原始字符串）, resolved_value（标准化值，如日期转 YYYY-MM-DD）。\n"
            f"不要包含解释，只返回 JSON。"
        )
        try:
            raw = self.llm.generate(prompt)
            parsed = json.loads(raw)
            return self._parse_entities_from_llm(parsed)
        except Exception as e:
            self.logger.exception("Entity extraction failed")
            return []  # 或加入正则规则

    def _parse_entities_from_llm(self, entity_list: List[Dict]) -> List[EntityDTO]:
        entities = []
        for item in entity_list:
            try:
                name = item.get("name")
                value = item.get("value")
                if name is None or value is None:
                    continue
                resolved = item.get("resolved_value", value)
                conf = float(item.get("confidence", 1.0))
                entities.append(EntityDTO(
                    name=name,
                    value=value,
                    resolved_value=resolved,
                    confidence=conf
                ))
            except Exception as e:
                self.logger.exception(f"Skip invalid entity: {item}")
        self.logger.debug(f"成功提取实体，数量={len(entities)}")
        self.logger.debug(f"成功解析实体列表，有效实体数量={len(entities)}")
        return entities

    def _check_ambiguity(self, primary_conf: float, alternatives: List[Tuple[IntentType, float]]) -> bool:
        if not alternatives:
            return False
        top_alt_score = max(score for _, score in alternatives)
        is_ambiguous = (primary_conf - top_alt_score) < self.ambiguity_threshold
        self.logger.debug(f"歧义检查结果：primary_conf={primary_conf:.2f}, top_alt_score={top_alt_score:.2f}, is_ambiguous={is_ambiguous}")
        return is_ambiguous

    def _build_result(
        self,
        primary: IntentType,
        confidence: float,
        alternatives: List[Tuple[IntentType, float]],
        entities: List[EntityDTO],
        utterance: str,
        raw: dict,
        is_ambiguous: bool = False
    ) -> IntentRecognitionResultDTO:
        return IntentRecognitionResultDTO(
            primary_intent=primary,
            confidence=min(max(confidence, 0.0), 1.0),
            alternative_intents=alternatives,
            entities=entities,
            is_ambiguous=is_ambiguous,
            raw_nlu_output={
                "original_utterance": utterance,
                **raw
            }
        )
    
    def _format_context_for_llm(self, state: DialogStateDTO) -> str:
        """将结构化状态转换为 LLM 可读的自然语言描述"""
        if not state:
            return "当前无活跃会话上下文。"
        
        parts = []
        
        # 1. 检查是否有正在草拟的任务
        if state.active_task_draft:
            draft = state.active_task_draft
            status_desc = f"用户正在创建一个 '{draft.task_type}' 任务 (状态: {draft.status})。"
            
            # 提取已填和缺失信息
            filled = [k for k, v in draft.slots.items() if v.confirmed]
            missing = draft.missing_slots
            
            if missing:
                status_desc += f" 正在等待用户提供: {', '.join(missing)}。"
            elif filled:
                status_desc += f" 已收集信息: {', '.join(filled)}。"
                
            parts.append(status_desc)
            
            # 关键：告诉 LLM 此时的预期
            parts.append("【重要提示】此时用户的短语（如时间、地点、人名、确认/拒绝）极大概率是在【修改任务/填充参数】，而非闲聊。")

        # 2. 检查是否有正在执行的任务
        elif state.active_task_execution:
            parts.append(f"当前有一个任务正在执行中 (TaskID: {state.active_task_execution})。")
            
        # 3. 检查澄清状态
        if state.requires_clarification:
            parts.append(f"系统上一轮发起了澄清提问：{state.clarification_message}")

        if not parts:
            return "当前无活跃任务，处于空闲状态。"
            
        return "\n".join(parts)
    def judge_special_intent(self, user_input: str, dialog_state: DialogStateDTO) -> str:
        """判断特殊意图：确认、修改草稿或拒绝（使用LLM）"""
        self.logger.info(f"开始判断特殊意图，user_input={user_input[:50]}...")
        context_desc = self._format_context_for_llm(dialog_state)
        
        prompt = (
            f"你是一个意图识别助手。请判断用户输入的特殊意图类型。\n\n"
            f"【当前上下文状态】\n{context_desc}\n\n"
            f"【用户输入】\n{user_input}\n\n"
            f"【可能的意图类型】\n"
            f"1. CONFIRM：用户确认当前操作或任务信息\n"
            f"2. CANCEL：用户拒绝当前操作或取消任务\n"
            f"3. MODIFY：用户想要修改当前任务的信息\n"
            f"4. 无特殊意图：返回空字符串\n\n"
            f"【判断规则】\n"
            f"1. 考虑当前上下文状态，理解用户输入的真实意图\n"
            f"2. 只有明确的确认、拒绝或修改意图才返回对应类型\n"
            f"3. 否则返回空字符串\n\n"
            f"请严格按照以下JSON格式返回，不要包含任何其他内容：\n"
            f"{{\"intent_type\": \"CONFIRM\" 或 \"CANCEL\" 或 \"MODIFY\" 或 \"\"}}"
        )
        
        try:
            response: dict = self.llm.generate(prompt, parse_json=True)
            self.logger.info(f"Special intent LLM Response: {str(response)}")
            intent_type = response.get("intent_type", "")
            
            # 验证返回值是否合法
            if intent_type in ["CONFIRM", "CANCEL", "MODIFY", ""]:
                self.logger.info(f"成功判断特殊意图，结果={intent_type}")
                return intent_type
            else:
                self.logger.warning(f"Invalid special intent type: {intent_type}, returning empty string")
                return ""
                
        except Exception as e:
            self.logger.exception("Special intent LLM failed")
            # 降级为关键字匹配
            lower_input = user_input.lower()
            
            # 检查确认意图
            confirm_keywords = ["确认", "是的", "对的", "好的", "行", "没问题", "可以", "同意", "ok", "yes"]
            if any(kw in lower_input for kw in confirm_keywords):
                self.logger.info(f"成功判断特殊意图，结果=CONFIRM")
                return "CONFIRM"
            
            # 检查拒绝意图
            cancel_keywords = ["取消", "拒绝", "不", "不行", "不要", "不对", "no", "取消操作", "停止"]
            if any(kw in lower_input for kw in cancel_keywords):
                self.logger.info(f"成功判断特殊意图，结果=CANCEL")
                return "CANCEL"
            
            # 检查修改草稿意图
            modify_keywords = ["修改", "编辑", "更新", "改一下", "调整", "换", "重新", "变更"]
            if any(kw in lower_input for kw in modify_keywords):
                self.logger.info(f"成功判断特殊意图，结果=MODIFY")
                return "MODIFY"
            
            # 默认返回空字符串，表示不是特殊意图
            self.logger.info(f"成功判断特殊意图，结果=无特殊意图")
            return ""