from typing import Dict, Any, List, Optional
from .interface import ITaskQueryManager
from ...common import (
    TaskSummary,
    TaskExecutionContextDTO
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonTaskQueryManager(ITaskQueryManager):
    """任务查询管理器 - 查询任务的状态和结果"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务查询管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
    
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
    
    def _parse_query_filters(self, intent_result: IntentRecognitionResultDTO, last_mentioned_task_id: Optional[str] = None) -> Dict[str, Any]:
        """解析查询条件
        
        Args:
            intent_result: 意图识别结果DTO
            last_mentioned_task_id: 最后提及的任务ID（用于指代消解）
            
        Returns:
            查询过滤条件字典
        """
        filters = {}
        utterance = intent_result.raw_nlu_output.get("original_utterance", "").lower()
        
        # 2.1 处理时间范围
        if any(keyword in utterance for keyword in ["昨天", "昨天的"]):
            filters["time_range"] = "yesterday"
        elif any(keyword in utterance for keyword in ["今天", "今天的"]):
            filters["time_range"] = "today"
        elif any(keyword in utterance for keyword in ["本周", "本周的"]):
            filters["time_range"] = "this_week"
        elif any(keyword in utterance for keyword in ["上月", "上个月"]):
            filters["time_range"] = "last_month"
        
        # 2.2 处理状态过滤
        if any(keyword in utterance for keyword in ["运行中", "正在运行"]):
            filters["status"] = "RUNNING"
        elif any(keyword in utterance for keyword in ["已完成", "完成的"]):
            filters["status"] = "COMPLETED"
        elif any(keyword in utterance for keyword in ["失败", "失败的"]):
            filters["status"] = "FAILED"
        elif any(keyword in utterance for keyword in ["未开始"]):
            filters["status"] = "NOT_STARTED"
        
        # 2.3 处理类型过滤
        if any(keyword in utterance for keyword in ["爬虫", "爬取"]):
            filters["task_type"] = "CRAWLER"
        elif any(keyword in utterance for keyword in ["预订", "预约"]):
            filters["task_type"] = "BOOKING"
        
        # 2.4 处理指代消解
        if any(keyword in utterance for keyword in ["那个", "刚才", "最近"]):
            if last_mentioned_task_id:
                filters["task_id"] = last_mentioned_task_id
        
        # 2.5 处理实体中的过滤条件
        for entity in intent_result.entities:
            if entity.name == "task_type":
                filters["task_type"] = entity.resolved_value
            elif entity.name == "status":
                filters["status"] = entity.resolved_value
            elif entity.name == "time_range":
                filters["time_range"] = entity.resolved_value
        
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