# orchestrator.py（增强版）
from .models.task import Task, TaskType, TaskStatus, ScheduleConfig
from .services.task_registry import TaskRegistry
import re

class TaskOrchestrator:
    def __init__(self, memory_manager: UnifiedMemoryManager):
        self.memory = memory_manager
        self.qwen = memory_manager.qwen

    def route_user_intent(self, user_input: str, user_id: str) -> str:
        """
        智能路由：判断用户是想
        - 创建新任务？
        - 控制已有任务（启动/停止/修改）？
        - 对历史任务评论/修正？
        """
        prompt = f"""
你是一个任务意图分类器。请判断用户输入属于以下哪一类：

A. 创建新任务（包括一次性或循环任务）
B. 控制已有任务（如“开始/停止/修改/删除 某个任务”）
C. 对历史任务追加评论或修正结果（如“上次那个任务结果错了”、“补充一点”）
D. 查询任务状态

用户输入：{user_input}

只输出一个字母：A / B / C / D
"""
        intent = self.qwen.generate(prompt, max_tokens=10, temperature=0.0).strip()

        if intent == "A":
            return self._handle_create_task(user_input, user_id)
        elif intent == "B":
            return self._handle_control_task(user_input, user_id)
        elif intent == "C":
            return self._handle_comment_or_correct(user_input, user_id)
        elif intent == "D":
            return self._handle_query_tasks(user_id)
        else:
            # 默认当作新任务
            return self._handle_create_task(user_input, user_id)

    def _handle_create_task(self, user_input: str, user_id: str) -> str:
        # ...（复用之前逻辑，但创建 Task 对象并存入 registry）
        plan = self._parse_task_plan(user_input, user_id)
        task = Task(
            id=str(uuid.uuid4()),
            user_id=user_id,
            type=TaskType.RECURRING if plan.is_recurring else TaskType.ONCE,
            goal=plan.goal,
            original_input=user_input,
            subtasks=[st.dict() for st in plan.subtasks],
            schedule=plan.schedule,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        TaskRegistry.create_task(task)
        
        if task.type == TaskType.RECURRING:
            self._schedule_recurring_task(task)
            return f"✅ 已创建循环任务：{task.goal}（ID: {task.id[:8]}）"
        else:
            result = self._execute_task_now(task)
            return result

    def _handle_control_task(self, user_input: str, user_id: str) -> str:
        # 示例：用户说“停止上周的周报任务”
        task = TaskRegistry.find_task_by_description(user_id, user_input)
        if not task:
            return "⚠️ 未找到匹配的任务。请更具体地描述，如‘停止周报任务’。"

        if "停止" in user_input or "暂停" in user_input:
            TaskRegistry.update_task(task.id, {"status": TaskStatus.PAUSED})
            return f"⏸ 已暂停任务：{task.goal}"
        elif "开始" in user_input or "恢复" in user_input:
            TaskRegistry.update_task(task.id, {"status": TaskStatus.PENDING})
            return f"▶️ 已恢复任务：{task.goal}"
        elif "修改时间" in user_input or "改到" in user_input:
            # 提取新时间（简化：假设用户说“改成每周五”）
            new_cron = self._extract_cron_from_text(user_input)
            if new_cron:
                TaskRegistry.update_task(task.id, {
                    "schedule": ScheduleConfig(cron=new_cron, next_run=self._calc_next_run(new_cron))
                })
                return f"📅 已更新循环时间为：{new_cron}"
            else:
                return "❓ 未能识别新的时间格式。"
        elif "删除" in user_input:
            TaskRegistry.update_task(task.id, {"status": TaskStatus.CANCELED})
            return f"🗑 已取消任务：{task.goal}"
        else:
            return "❓ 不支持的操作。可用指令：开始/停止/修改时间/删除"

    def _handle_comment_or_correct(self, user_input: str, user_id: str) -> str:
        # 示例：“上次发布会任务的结果漏了茶歇环节”
        task = TaskRegistry.find_task_by_description(user_id, user_input)
        if not task:
            return "⚠️ 未找到相关任务。"

        if "修正" in user_input or "错了" in user_input or "应该是" in user_input:
            # 提取修正内容
            correction = user_input.replace("上次", "").replace("任务", "").strip("：:，,")
            TaskRegistry.update_task(task.id, {"corrected_result": correction})
            # 同时写入记忆系统
            self.memory.add_memory_intelligently(f"对任务 '{task.goal}' 的修正：{correction}")
            return "✅ 已记录修正内容，并更新记忆。"
        else:
            # 视为评论
            TaskRegistry.add_comment(task.id, user_input)
            return "📝 已添加评论。"

    def _handle_query_tasks(self, user_id: str) -> str:
        tasks = TaskRegistry.list_user_tasks(user_id)
        if not tasks:
            return "📭 您还没有任何任务。"
        lines = []
        for t in tasks[:5]:  # 最近5个
            typ = "🔄循环" if t.type == TaskType.RECURRING else "⚡一次"
            lines.append(f"- [{typ}] {t.goal} | {t.status.value} | ID: {t.id[:8]}")
        return "📋 您的任务列表：\n" + "\n".join(lines)

    # --- 辅助方法 ---
    def _parse_task_plan(self, user_input: str, user_id: str):
        # 类似之前逻辑，但增加对循环任务的识别
        context = self.memory.build_conversation_context(user_input)
        prompt = f"""...（类似之前，但要求输出是否 recurring 和 cron）..."""
        # 返回包含 is_recurring, schedule 等字段的对象
        ...

    def _schedule_recurring_task(self, task: Task):
        # 集成 APScheduler 或放入队列由后台轮询
        print(f"[SCHEDULER] 将任务 {task.id} 加入循环调度: {task.schedule}")

    def _execute_task_now(self, task: Task) -> str:
        # 执行并更新状态
        ...
        TaskRegistry.update_task(task.id, {"status": TaskStatus.COMPLETED})
        return "✅ 任务已完成。"