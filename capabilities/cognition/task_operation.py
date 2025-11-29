"""任务操作分类能力 - 使用LLM分类用户对任务的操作意图"""
import logging
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod

from common.types.task_operation import TaskOperationType, TaskOperationCategory, get_operation_category
from capabilities.llm.interface import ILLMCapability


logger = logging.getLogger(__name__)


class ITaskOperationCapability(ABC):
    """任务操作分类能力接口"""

    @abstractmethod
    def classify_operation(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分类任务操作

        Args:
            user_input: 用户输入
            context: 上下文信息（如历史任务、当前状态等）

        Returns:
            Dict包含:
                - operation_type: TaskOperationType
                - category: TaskOperationCategory
                - target_task_id: Optional[str] - 目标任务ID（如果适用）
                - parameters: Dict[str, Any] - 提取的参数
                - confidence: float - 置信度
        """
        raise NotImplementedError


class TaskOperationCapability(ITaskOperationCapability):
    """任务操作分类能力实现"""

    def __init__(self, llm_capability: ILLMCapability):
        """
        初始化

        Args:
            llm_capability: LLM能力实例
        """
        self.llm = llm_capability
        self.logger = logging.getLogger("TaskOperationCapability")

    def initialize(self, config: Dict[str, Any] = None):
        """初始化能力"""
        self.logger.info("TaskOperationCapability initialized")

    def classify_operation(self, user_input: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        分类任务操作

        使用LLM分析用户输入，判断是哪种任务操作
        """
        context = context or {}

        # 构建提示词
        prompt = self._build_classification_prompt(user_input, context)

        try:
            # 调用LLM
            response = self.llm.generate(prompt, temperature=0.1, max_tokens=500)

            # 解析响应
            result = self._parse_llm_response(response, user_input)

            self.logger.info(f"任务操作分类: {result['operation_type'].value}, 置信度: {result['confidence']}")

            return result

        except Exception as e:
            self.logger.error(f"任务操作分类失败: {e}")
            # 返回默认结果
            return {
                "operation_type": TaskOperationType.NEW_TASK,
                "category": TaskOperationCategory.CREATION,
                "target_task_id": None,
                "parameters": {},
                "confidence": 0.0,
                "error": str(e)
            }

    def _build_classification_prompt(self, user_input: str, context: Dict[str, Any]) -> str:
        """构建分类提示词"""

        # 获取可能的历史任务
        recent_tasks = context.get("recent_tasks", [])
        task_context = ""
        if recent_tasks:
            task_context = "\n最近的任务:\n"
            for task in recent_tasks[:5]:
                task_context += f"- ID: {task.get('id', 'unknown')}, 描述: {task.get('description', '')}\n"

        prompt = f"""你是一个任务操作分类专家。请分析用户输入，判断用户想要执行的任务操作类型。

用户输入: {user_input}

{task_context}

可能的操作类型包括：

**创建类:**
- new_task: 创建新的单次任务（如"帮我分析数据"）
- new_loop_task: 创建循环任务（如"每天早上9点提醒我"）
- new_delayed_task: 创建延时任务（如"3小时后提醒我"）
- new_scheduled_task: 创建定时任务（如"明天下午2点执行报表"）

**执行控制类:**
- execute_task: 立即执行任务（如"执行任务123"）
- trigger_loop_task: 立即触发循环任务（如"立即执行每日报表"）
- pause_task: 暂停任务（如"暂停任务456"）
- resume_task: 恢复任务（如"继续执行任务456"）
- cancel_task: 取消任务（如"取消任务789"）
- retry_task: 重试任务（如"重新执行失败的任务"）

**循环任务管理:**
- modify_loop_interval: 修改循环间隔（如"把每日报表改成每周"）
- pause_loop: 暂停循环（如"暂停每日提醒"）
- resume_loop: 恢复循环（如"恢复每日提醒"）
- cancel_loop: 取消循环任务（如"删除每日报表任务"）

**修改类:**
- modify_task_params: 修改任务参数
- revise_result: 修改任务结果（如"修改上次分析结果"）
- revise_process: 修改任务过程（如"改变执行步骤"）
- comment_on_task: 对任务添加评论（如"给任务123加个备注"）
- update_task_description: 更新任务描述

**查询类:**
- query_task_status: 查询任务状态（如"任务123执行得怎么样了"）
- query_task_result: 查询任务结果（如"上次分析的结果是什么"）
- query_task_history: 查询任务历史
- list_tasks: 列出任务列表（如"显示所有任务"）

请以JSON格式返回分类结果：
{{
    "operation_type": "操作类型",
    "target_task_id": "目标任务ID（如果有）",
    "parameters": {{
        "关键参数": "值"
    }},
    "confidence": 0.95,
    "reasoning": "分类理由"
}}

只返回JSON，不要其他内容。
"""
        return prompt

    def _parse_llm_response(self, response: str, user_input: str) -> Dict[str, Any]:
        """解析LLM响应"""
        import json
        import re

        try:
            # 提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

            # 解析操作类型
            operation_type_str = data.get("operation_type", "new_task")
            try:
                operation_type = TaskOperationType(operation_type_str)
            except ValueError:
                self.logger.warning(f"未知的操作类型: {operation_type_str}, 使用默认值")
                operation_type = TaskOperationType.NEW_TASK

            # 获取分类
            category = get_operation_category(operation_type)

            return {
                "operation_type": operation_type,
                "category": category,
                "target_task_id": data.get("target_task_id"),
                "parameters": data.get("parameters", {}),
                "confidence": data.get("confidence", 0.5),
                "reasoning": data.get("reasoning", "")
            }

        except Exception as e:
            self.logger.error(f"解析LLM响应失败: {e}, 响应: {response}")
            # 使用简单规则作为fallback
            return self._fallback_classification(user_input)

    def _fallback_classification(self, user_input: str) -> Dict[str, Any]:
        """当LLM解析失败时使用的简单规则分类"""
        user_input_lower = user_input.lower()

        # 简单的关键词匹配
        if any(kw in user_input_lower for kw in ["取消", "删除", "停止"]):
            operation_type = TaskOperationType.CANCEL_TASK
        elif any(kw in user_input_lower for kw in ["暂停"]):
            operation_type = TaskOperationType.PAUSE_TASK
        elif any(kw in user_input_lower for kw in ["继续", "恢复"]):
            operation_type = TaskOperationType.RESUME_TASK
        elif any(kw in user_input_lower for kw in ["修改结果", "更改结果"]):
            operation_type = TaskOperationType.REVISE_RESULT
        elif any(kw in user_input_lower for kw in ["查询", "查看", "状态"]):
            operation_type = TaskOperationType.QUERY_TASK_STATUS
        elif any(kw in user_input_lower for kw in ["每天", "每周", "定时", "循环"]):
            operation_type = TaskOperationType.NEW_LOOP_TASK
        else:
            operation_type = TaskOperationType.NEW_TASK

        category = get_operation_category(operation_type)

        return {
            "operation_type": operation_type,
            "category": category,
            "target_task_id": None,
            "parameters": {},
            "confidence": 0.3,  # 低置信度
            "reasoning": "Fallback classification based on keywords"
        }
