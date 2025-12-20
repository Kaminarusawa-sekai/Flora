from typing import Dict, Any, List, Optional
import json
import logging
from .interface import ITaskQueryManagerCapability
from ...common import (
    TaskSummary,
    TaskExecutionContextDTO,
    IntentRecognitionResultDTO,
    EntityDTO
)
from ...external.client import TaskStorage
from ..llm.interface import ILLMCapability

logger = logging.getLogger(__name__)

class CommonTaskQuery(ITaskQueryManagerCapability):
    """任务查询管理器 - 查询任务的状态和结果"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务查询管理器"""
        self.config = config
        # 获取LLM能力
        self._llm = None
        # 初始化任务存储
        self.task_storage = TaskStorage()
    
    @property
    def llm(self):
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
    
    def shutdown(self) -> None:
        """关闭任务查询管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "task_query"
    
    def process_query_intent(self, intent_result: IntentRecognitionResultDTO, user_id: str, last_mentioned_task_id: Optional[str] = None) -> Dict[str, Any]:
        """处理查询意图，返回匹配的任务列表
        
        Args:
            intent_result: 意图识别结果DTO
            user_id: 用户ID
            last_mentioned_task_id: 最后提及的任务ID（用于指代消解）
            
        Returns:
            结构化的任务查询结果，可直接用于SystemResponseDTO.displayData
        """
        # 1. 解析查询条件
        filters = self._parse_query_filters(intent_result, last_mentioned_task_id)
        
        # 2. 调用任务存储层查询任务
        tasks = self._query_tasks(user_id, filters)
        
        # 3. 生成结构化响应
        response_data = self._format_query_result(tasks)
        
        return response_data
    
    def _parse_query_filters_rule_based(self, intent_result: IntentRecognitionResultDTO, last_mentioned_task_id: Optional[str] = None) -> Dict[str, Any]:
        """基于规则的查询条件解析
        
        Args:
            intent_result: 意图识别结果DTO
            last_mentioned_task_id: 最后提及的任务ID（用于指代消解）
            
        Returns:
            查询过滤条件字典
        """
        filters = {}
        utterance = intent_result.raw_nlu_output.get("original_utterance", "").lower()
        
        # 1. 先处理实体中的过滤条件（优先使用NLU实体结果）
        for entity in intent_result.entities:
            if entity.name == "task_type":
                filters["task_type"] = entity.resolved_value
            elif entity.name == "status":
                filters["execution_status"] = entity.resolved_value
            elif entity.name == "time_range":
                filters["time_range"] = entity.resolved_value
            elif entity.name == "task_id":
                filters["task_id"] = entity.resolved_value
        
        # 2. 处理时间范围（关键词匹配，作为实体结果的补充）
        if "time_range" not in filters:
            if any(keyword in utterance for keyword in ["昨天", "昨天的"]):
                filters["time_range"] = "yesterday"
            elif any(keyword in utterance for keyword in ["今天", "今天的", "今日"]):
                filters["time_range"] = "today"
            elif any(keyword in utterance for keyword in ["本周", "本周的"]):
                filters["time_range"] = "this_week"
            elif any(keyword in utterance for keyword in ["上月", "上个月"]):
                filters["time_range"] = "last_month"
            elif any(keyword in utterance for keyword in ["上周", "上星期"]):
                filters["time_range"] = "last_week"
        
        # 3. 处理状态过滤（关键词匹配，作为实体结果的补充）
        if "execution_status" not in filters:
            if any(keyword in utterance for keyword in ["运行中", "正在运行", "进行中", "执行中"]):
                filters["execution_status"] = "RUNNING"
            elif any(keyword in utterance for keyword in ["已完成", "完成的", "结束的", "做完了"]):
                filters["execution_status"] = "COMPLETED"
            elif any(keyword in utterance for keyword in ["失败", "失败的", "出错", "错误"]):
                filters["execution_status"] = "FAILED"
            elif any(keyword in utterance for keyword in ["未开始", "待处理", "待执行", "等待中", "未完成"]):
                filters["execution_status"] = "NOT_STARTED"
            elif any(keyword in utterance for keyword in ["暂停", "已暂停", "暂停中"]):
                filters["control_status"] = "PAUSED"
        
        # 4. 处理类型过滤（关键词匹配，作为实体结果的补充）
        if "task_type" not in filters:
            if any(keyword in utterance for keyword in ["爬虫", "爬取", "抓取"]):
                filters["task_type"] = "web_crawler"
            elif any(keyword in utterance for keyword in ["数据分析", "统计", "分析"]):
                filters["task_type"] = "data_analysis"
            elif any(keyword in utterance for keyword in ["邮件", "发送邮件", "营销邮件"]):
                filters["task_type"] = "email_sender"
            elif any(keyword in utterance for keyword in ["文件", "处理文件", "Excel"]):
                filters["task_type"] = "file_processing"
        
        # 5. 处理指代消解
        if "task_id" not in filters:
            # 单数指代
            if any(keyword in utterance for keyword in ["那个", "刚才", "最近", "这个", "当前"]):
                if last_mentioned_task_id:
                    filters["task_id"] = last_mentioned_task_id
            # 复数指代
            elif any(keyword in utterance for keyword in ["那些", "所有", "全部"]):
                # 不绑定具体task_id，返回所有匹配任务
                pass
        
        # 6. 默认排序
        filters.setdefault("sort_by", "created_at")
        filters.setdefault("sort_order", "desc")
        
        return filters
    
    def _build_parsing_prompt(self, utterance: str, entities: List[Any], last_mentioned_task_id: Optional[str], user_context: Optional[Dict] = None) -> str:
        """构建LLM解析提示词
        
        Args:
            utterance: 用户原始查询语句
            entities: NLU识别出的实体列表
            last_mentioned_task_id: 最后提及的任务ID
            user_context: 用户上下文信息
            
        Returns:
            构建好的提示词
        """
        entities_str = json.dumps([{"name": e.name, "value": e.value, "resolved_value": e.resolved_value} for e in entities], ensure_ascii=False)
        
        prompt = f"""你是一个任务查询解析器。请根据用户的自然语言查询，提取结构化的过滤条件。

已知信息：
- 用户最近提到的任务ID：{last_mentioned_task_id}
- NLU识别出的实体：{entities_str}

用户查询："{utterance}"

请输出一个 JSON 对象，包含以下可选字段：
- time_range: "today" | "yesterday" | "this_week" | "last_week" | "last_month" | "custom"（若为 custom，需提供 start_time/end_time）
- execution_status: "NOT_STARTED" | "RUNNING" | "COMPLETED" | "FAILED" | "ERROR" | "CANCELLED" | "AWAITING_USER_INPUT"
- task_type: 任务类型，如 "web_crawler" | "data_analysis" | "email_sender" | "file_processing"
- task_id: string（仅当明确指代单个任务时）
- tags: [string]（任务标签列表）
- negate: boolean（是否是否定查询，如"除了..."）
- keywords: [string]（用于全文搜索的关键词）

只输出 JSON，不要解释。"""
        
        return prompt
    
    def _get_filter_schema(self) -> Dict[str, Any]:
        """获取过滤条件的JSON Schema
        
        Returns:
            JSON Schema字典
        """
        return {
            "type": "object",
            "properties": {
                "time_range": {
                    "type": "string",
                    "enum": ["today", "yesterday", "this_week", "last_week", "last_month", "custom"]
                },
                "execution_status": {
                    "type": "string",
                    "enum": ["NOT_STARTED", "RUNNING", "COMPLETED", "FAILED", "ERROR", "CANCELLED", "AWAITING_USER_INPUT"]
                },
                "task_type": {
                    "type": "string"
                },
                "task_id": {
                    "type": "string"
                },
                "tags": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                },
                "negate": {
                    "type": "boolean"
                },
                "keywords": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    }
                }
            },
            "additionalProperties": False
        }
    
    def _validate_and_clean_filters(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和清理过滤条件
        
        Args:
            filters: LLM生成的过滤条件
            
        Returns:
            验证和清理后的过滤条件
        """
        # 移除None值
        cleaned_filters = {k: v for k, v in filters.items() if v is not None}
        
        # 添加默认排序
        cleaned_filters.setdefault("sort_by", "created_at")
        cleaned_filters.setdefault("sort_order", "desc")
        
        return cleaned_filters
    
    def _is_complex_query(self, utterance: str) -> bool:
        """判断查询是否复杂
        
        Args:
            utterance: 用户原始查询语句
            
        Returns:
            是否为复杂查询
        """
        # 复杂查询的特征
        complex_features = [
            "除了", "不是", "不包括",  # 否定词
            "并且", "而且", "同时", "还有",  # 多条件
            "类似", "相同", "相关",  # 相似性查询
            "没跑完", "卡住了", "搞定了吗",  # 口语化表达
            "最近的", "之前的", "之前的那个",  # 时间+指代
        ]
        
        # 长度超过20字符也视为复杂查询
        if len(utterance) > 20:
            return True
        
        # 检查是否包含复杂特征
        for feature in complex_features:
            if feature in utterance:
                return True
        
        return False
    
    def _has_meaningful_filters(self, filters: Dict[str, Any]) -> bool:
        """判断过滤条件是否有意义
        
        Args:
            filters: 过滤条件字典
            
        Returns:
            是否有意义的过滤条件
        """
        # 排除默认排序字段
        meaningful_keys = [k for k in filters.keys() if k not in ["sort_by", "sort_order"]]
        return len(meaningful_keys) > 0
    
    def _parse_query_filters_with_llm(self, intent_result: IntentRecognitionResultDTO, last_mentioned_task_id: Optional[str] = None) -> Dict[str, Any]:
        """使用LLM辅助解析查询条件
        
        Args:
            intent_result: 意图识别结果DTO
            last_mentioned_task_id: 最后提及的任务ID（用于指代消解）
            
        Returns:
            查询过滤条件字典
        """
        utterance = intent_result.raw_nlu_output.get("original_utterance", "")
        
        # 构造prompt
        prompt = self._build_parsing_prompt(utterance, intent_result.entities, last_mentioned_task_id)
        
        try:
            # 调用LLM（要求输出JSON）
            response = self.llm.generate(
                prompt=prompt,
                response_format={"type": "json_object"}
            )
            
            # 解析LLM响应
            filters = json.loads(response.strip())
            return self._validate_and_clean_filters(filters)
        except Exception as e:
            logger.warning(f"LLM parsing failed, fallback to rule-based: {e}")
            return self._parse_query_filters_rule_based(intent_result, last_mentioned_task_id)
    
    def _parse_query_filters(self, intent_result: IntentRecognitionResultDTO, last_mentioned_task_id: Optional[str] = None) -> Dict[str, Any]:
        """查询条件解析（混合策略）
        
        Args:
            intent_result: 意图识别结果DTO
            last_mentioned_task_id: 最后提及的任务ID（用于指代消解）
            
        Returns:
            查询过滤条件字典
        """
        utterance = intent_result.raw_nlu_output.get("original_utterance", "").lower()
        
        # 先尝试规则解析
        filters = self._parse_query_filters_rule_based(intent_result, last_mentioned_task_id)
        
        # 如果规则解析结果太弱，或查询复杂，启用LLM
        if self._is_complex_query(utterance) or not self._has_meaningful_filters(filters):
            llm_filters = self._parse_query_filters_with_llm(intent_result, last_mentioned_task_id)
            # 合并结果，LLM结果优先级更高
            filters.update(llm_filters)
        
        return filters
    
    def _query_tasks(self, user_id: str, filters: Dict[str, Any]) -> List[TaskExecutionContextDTO]:
        """查询任务执行上下文
        
        Args:
            user_id: 用户ID
            filters: 查询过滤条件
            
        Returns:
            匹配的任务执行上下文列表
        """
        # 调用任务存储层查询任务
        tasks = self.task_storage.list_execution_contexts(user_id, filters)
        
        # 这里可以添加排序和分页逻辑
        
        return tasks
    
    def _format_query_result(self, tasks: List[TaskExecutionContextDTO]) -> Dict[str, Any]:
        """格式化查询结果为结构化数据
        
        Args:
            tasks: 任务执行上下文列表
            
        Returns:
            结构化的查询结果
        """
        # 生成任务摘要列表
        task_summaries = []
        for task in tasks:
            task_summary = {
                "task_id": task.task_id,
                "title": task.title,
                "task_type": task.task_type,
                "status": task.execution_status,
                "control_status": task.control_status,
                "created_at": task.created_at,
                "tags": task.tags,
                "progress": self._calculate_progress(task)
            }
            task_summaries.append(task_summary)
        
        # 生成结构化响应
        response_data = {
            "type": "TASK_LIST",
            "total": len(task_summaries),
            "tasks": task_summaries,
            "message": f"找到 {len(task_summaries)} 个任务"
        }
        
        return response_data
    
    def _calculate_progress(self, task: TaskExecutionContextDTO) -> float:
        """计算任务进度
        
        Args:
            task: 任务执行上下文DTO
            
        Returns:
            任务进度（0.0-1.0）
        """
        # 简化的进度计算，实际应该根据任务执行情况计算
        status_progress_map = {
            "NOT_STARTED": 0.0,
            "RUNNING": 0.5,
            "COMPLETED": 1.0,
            "FAILED": 0.0,
            "ERROR": 0.0,
            "CANCELLED": 0.0
        }
        
        return status_progress_map.get(task.execution_status, 0.0)