"""任务操作分类能力 - 使用LLM分类用户对任务的操作意图"""
import logging
from typing import Dict, Any, Optional

from common.types.task_operation import TaskOperationType, TaskOperationCategory, get_operation_category
from capabilities.llm.interface import ILLMCapability
from .interface import ITaskOperationCapability


logger = logging.getLogger(__name__)


class CommonTaskOperation(ITaskOperationCapability):
    """任务操作分类能力实现"""

    def __init__(self):
        """
        初始化

        Args:
            
        """
        self.llm = None
        self.logger = logging.getLogger("TaskOperationCapability")

    def initialize(self, config: Dict[str, Any] = None):
        """初始化能力"""
        self.logger.info("TaskOperationCapability initialized")

    def shutdown(self):
        """关闭能力"""
        self.logger.info("TaskOperationCapability shutdown")
    
    def is_available(self) -> bool:
        """检查能力是否可用"""
        return self.llm is not None

    def get_capability_type(self) -> str:
        """获取能力类型"""
        return "common_task_operation"

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
            if not self.llm:
                from capabilities import get_capability
                from capabilities.llm.interface import ILLMCapability
                self.llm = get_capability("llm", expected_type=ILLMCapability)
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


        ##TODO：动态传入类型
        prompt = f"""你是一个任务操作分类专家。你的核心职责是区分用户是想要【执行一个新动作】还是想要【管理/询问已有任务的状态】。

用户输入: {user_input}

{task_context}

---
### ⚠️ 核心区分原则 (Critical Distinction)
在做出判断前，请先思考以下区别：
1. **获取业务数据/信息 = 创建任务 (new_task)**
   - 如果用户说 "查询上月销售数据"、"帮我找一下XXX文档"、"现在几点了"、"分析这份报表"。
   - 尽管包含了"查询"二字，但这本质上是要求 Agent **去执行一个动作** 来获取信息。
   - **判定为**: `new_task`。

2. **询问任务运行状况 = 查询任务 (query_task_...)**
   - 如果用户说 "刚才那个任务跑完了吗"、"还有多久结束"、"显示任务列表"。
   - 这是在询问 **Agent 系统内部** 的调度状态。
   - **判定为**: `query_task_status` 或 `list_tasks`。

---

请从以下严格定义的【操作类型列表】中选择一个。
⚠️ 重要：必须精确使用列表中的字符串。

**1. 创建类 (Doing Work):**
- new_task: 创建新的执行任务。包括：计算、**查询业务数据**、检索信息、生成内容、回答问题。（如"查一下北京天气"、"查询上月报表"、"分析数据"）
- new_loop_task: 创建循环任务（如"每天早上9点查一下数据"）
- new_delayed_task: 创建延时任务（如"3小时后提醒我"）
- new_scheduled_task: 创建定时任务（如"明天下午2点执行"）

**2. 执行控制类 (Managing Work):**
- execute_task: 立即执行某个已存在的任务ID
- trigger_loop_task: 立即触发某个已有的循环
- pause_task: 暂停正在运行的任务
- resume_task: 恢复暂停的任务
- cancel_task: 取消/终止任务
- retry_task: 重试失败的任务

**3. 循环任务管理:**
- modify_loop_interval: 修改循环频率
- pause_loop: 暂停循环调度
- resume_loop: 恢复循环调度
- cancel_loop: 删除/停止循环任务

**4. 修改类:**
- modify_task_params: 修改任务参数
- revise_result: 修改任务产生的结果（如"把结果里的A改成B"）
- comment_on_task: 对任务添加备注

**5. 系统状态查询类 (System State):**
- query_task_status: 仅查询任务的**运行进度/状态**（如"任务失败了吗"、"还在跑吗"）
- query_task_result: 仅查询**已完成任务的输出记录**（如"调出刚才那个任务的生成结果"）
- list_tasks: 列出当前的任务队列

请以JSON格式返回分类结果：
{{
    "operation_type": "操作类型",
    "target_task_id": "目标任务ID（仅当用户明确指代了历史任务时填写，否则为null）",
    "parameters": {{
        "关键参数": "提取的值"
    }},
    "confidence": 0.95,
    "reasoning": "必须简述理由，说明为什么归类为此类型而不是其他"
}}

只返回JSON，不要其他内容。
"""
        return prompt

    def _parse_llm_response(self, response: str, user_input: str) -> Dict[str, Any]:
        """解析LLM响应 (增强版：包含模糊匹配容错)"""
        import json
        import re
        from difflib import get_close_matches  # 引入模糊匹配工具

        try:
            # 1. 提取JSON部分
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                data = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")

            # 2. 解析操作类型 (核心修改部分)
            operation_type_str = data.get("operation_type", "new_task")
            
            try:
                # 尝试 A: 精确匹配
                operation_type = TaskOperationType(operation_type_str)
                
            except ValueError:
                # 尝试 B: 模糊匹配 (处理幻觉/简写，如 query_result -> query_task_result)
                # 获取所有合法的枚举值列表
                valid_ops = [t.value for t in TaskOperationType]
                
                # cutoff=0.6 表示相似度至少要达到 60%，n=1 表示只取最像的一个
                matches = get_close_matches(operation_type_str, valid_ops, n=1, cutoff=0.6)
                
                if matches:
                    best_match = matches[0]
                    self.logger.info(f"LLM输出纠错: 将 '{operation_type_str}' 修正为 '{best_match}'")
                    operation_type = TaskOperationType(best_match)
                else:
                    # 尝试 C: 实在匹配不上，使用默认值
                    self.logger.warning(f"未知的操作类型: '{operation_type_str}' 且无近似匹配, 使用默认值 NEW_TASK")
                    operation_type = TaskOperationType.NEW_TASK

            # 3. 获取分类
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
