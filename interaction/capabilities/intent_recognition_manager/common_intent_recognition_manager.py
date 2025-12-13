import json
import logging
from typing import Dict, Any, List, Tuple, Optional
from collections import Counter

from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability
from .interface import IIntentRecognitionManagerCapability
from ...common import (
    IntentRecognitionResultDTO,
    IntentType,
    EntityDTO,
    UserInputDTO
)

logger = logging.getLogger(__name__)

# 枚举值映射
INTENT_NAME_TO_ENUM = {intent.value: intent for intent in IntentType}
ALLOWED_INTENT_NAMES = list(INTENT_NAME_TO_ENUM.keys())

class CommonIntentRecognition(IIntentRecognitionManagerCapability):
    """增强版意图识别：输出主意图 + 候选意图 + 实体 + 歧义标记"""

    def __init__(self):
        self.config = None
        self.llm = None
        self.ambiguity_threshold = 0.2

    def initialize(self, config: Dict[str, Any]) -> None:
        self.config = config
        self.llm = get_capability("llm", expected_type=ILLMCapability)
        self.ambiguity_threshold = config.get("ambiguity_threshold", 0.2)  # top1 - top2 < 此值则视为歧义
    
    def shutdown(self) -> None:
        pass
    
    def get_capability_type(self) -> str:
        return "nlu"
    
    def recognize_intent(self, user_input: UserInputDTO) -> IntentRecognitionResultDTO:
        utterance = user_input.utterance.strip()
        if not utterance:
            return self._build_result(
                primary=IntentType.IDLE,
                confidence=1.0,
                alternatives=[],
                entities=[],
                utterance=utterance,
                raw={}
            )

        # === 阶段1：是否任务相关？===
        stage1_prompt = (
            f"判断以下用户输入是否与任务管理相关（如创建、修改、查询、删除、暂停、恢复、重试、设置定时等）。\n"
            f"如果是，回复 'TASK'；否则回复 'IDLE'。\n\n"
            f"用户输入：{utterance}"
        )
        try:
            stage1_result = self.llm.generate(stage1_prompt).strip()
        except Exception as e:
            logger.warning("Stage1 LLM failed: %s", e)
            stage1_result = "TASK"

        if stage1_result != "TASK":
            return self._build_result(
                primary=IntentType.IDLE,
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
            logger.warning("LLM parsing failed, falling back to rule-based: %s", e)
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
            (["创建", "新建", "添加"], IntentType.CREATE, 0.9),
            (["修改", "编辑", "更新"], IntentType.MODIFY, 0.8),
            (["查询", "查看", "列表", "有哪些"], IntentType.QUERY, 0.9),
            (["删除"], IntentType.DELETE, 0.8),
            (["取消"], IntentType.CANCEL, 0.8),
            (["恢复", "继续"], IntentType.RESUME_TASK, 0.7),  # 默认是继续任务
            (["中断", "挂起"], IntentType.PAUSE, 0.7),
            (["重试"], IntentType.RETRY, 0.8),
            (["定时", "每天", "每周", "每小时", "计划"], IntentType.SET_SCHEDULE, 0.8),
        ]
        for keywords, intent, conf in rules:
            if any(kw in lower_utterance for kw in keywords):
                # 特殊处理“恢复中断”
                if intent == IntentType.RESUME_TASK and "中断" in lower_utterance:
                    return IntentType.RESUME, conf
                    
                return intent, conf
        return IntentType.IDLE, 0.6

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
            logger.debug("Entity extraction failed: %s", e)
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
                logger.debug("Skip invalid entity: %s, error: %s", item, e)
        return entities

    def _check_ambiguity(self, primary_conf: float, alternatives: List[Tuple[IntentType, float]]) -> bool:
        if not alternatives:
            return False
        top_alt_score = max(score for _, score in alternatives)
        return (primary_conf - top_alt_score) < self.ambiguity_threshold

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