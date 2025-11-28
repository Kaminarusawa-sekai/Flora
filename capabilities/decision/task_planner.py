from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from capabilities.capability_base import CapabilityBase
from capabilities.registry import CapabilityRegistry
from common.types.task import Task, TaskType, TaskStatus, ScheduleConfig
from external.repositories.task_repo import TaskRepository

class ITaskPlannerCapability(CapabilityBase):
    """Interface for task planning capability"""
    def generate_subtasks(self, task: Task) -> List[Task]:
        """Generate subtasks for a given task"""
        raise NotImplementedError
    
    def route_user_intent(self, user_input: str, user_id: str) -> str:
        """Route user intent to appropriate task handling"""
        raise NotImplementedError
    
    def execute_task(self, task: Task) -> str:
        """Execute a task"""
        raise NotImplementedError

class TaskPlannerCapability(ITaskPlannerCapability):
    """Task planning and orchestration capability"""
    def __init__(self):
        super().__init__()
        self.task_repo = TaskRepository()
        self.llm = None
    
    def initialize(self, config: Dict[str, Any] = None):
        """Initialize the capability"""
        from capabilities.llm.qwen_adapter import QwenAdapter
        self.llm = QwenAdapter()
        self.llm.initialize(config.get("llm", {}) if config else {})
    
    def shutdown(self):
        """Shutdown the capability"""
        pass
    
    def get_capability_type(self) -> str:
        """Return capability type"""
        return "decision"
    
    def generate_subtasks(self, task: Task) -> List[Task]:
        """Generate subtasks for a given task"""
        # This would typically use LLM to generate subtasks
        # For now, return an empty list as placeholder
        return []
    
    def route_user_intent(self, user_input: str, user_id: str) -> str:
        """Route user intent to appropriate task handling"""
        # Use LLM to classify intent
        prompt = f"""你是一个任务意图分类器。请判断用户输入属于以下哪一类：

A. 创建新任务（包括一次性或循环任务）
B. 控制已有任务（如“开始/停止/修改/删除 某个任务”）
C. 对历史任务追加评论或修正结果（如“上次那个任务结果错了”、“补充一点”）
D. 查询任务状态

用户输入：{user_input}

只输出一个字母：A / B / C / D
"""
        
        intent = self.llm.generate(prompt, max_tokens=10, temperature=0.0).strip()
        
        if intent == "A":
            return self._handle_create_task(user_input, user_id)
        elif intent == "B":
            return self._handle_control_task(user_input, user_id)
        elif intent == "C":
            return self._handle_comment_or_correct(user_input, user_id)
        elif intent == "D":
            return self._handle_query_tasks(user_id)
        else:
            # Default to creating new task
            return self._handle_create_task(user_input, user_id)
    
    def _handle_create_task(self, user_input: str, user_id: str) -> str:
        """Handle task creation"""
        # Simplified implementation - in real scenario would use LLM to parse task details
        task = Task(
            task_id=str(uuid.uuid4()),
            description=user_input,
            task_type=TaskType.ONE_TIME,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            user_id=user_id,
            goal=user_input,
            original_input=user_input
        )
        
        self.task_repo.create_task(task)
        result = self.execute_task(task)
        return result
    
    def _handle_control_task(self, user_input: str, user_id: str) -> str:
        """Handle task control commands"""
        # Simplified implementation
        task = self.task_repo.find_task_by_reference(user_id, user_input)
        if not task:
            return "⚠️ 未找到匹配的任务。请更具体地描述，如‘停止周报任务’。"
        
        if "停止" in user_input or "暂停" in user_input:
            self.task_repo.update_task(task.task_id, {"status": TaskStatus.PAUSED})
            return f"⏸ 已暂停任务：{task.goal}"
        elif "开始" in user_input or "恢复" in user_input:
            self.task_repo.update_task(task.task_id, {"status": TaskStatus.CREATED})
            return f"▶️ 已恢复任务：{task.goal}"
        elif "删除" in user_input:
            self.task_repo.update_task(task.task_id, {"status": TaskStatus.CANCELLED})
            return f"🗑 已取消任务：{task.goal}"
        else:
            return "❓ 不支持的操作。可用指令：开始/停止/删除"
    
    def _handle_comment_or_correct(self, user_input: str, user_id: str) -> str:
        """Handle task comments or corrections"""
        # Simplified implementation
        task = self.task_repo.find_task_by_reference(user_id, user_input)
        if not task:
            return "⚠️ 未找到相关任务。"
        
        if "修正" in user_input or "错了" in user_input or "应该是" in user_input:
            # Extract correction content
            correction = user_input.replace("上次", "").replace("任务", "").strip("：:,，")
            self.task_repo.update_task(task.task_id, {"corrected_result": correction})
            return "✅ 已记录修正内容。"
        else:
            # Treat as comment
            self.task_repo.add_comment(task.task_id, user_input)
            return "📝 已添加评论。"
    
    def _handle_query_tasks(self, user_id: str) -> str:
        """Handle task queries"""
        tasks = self.task_repo.list_user_tasks(user_id)
        if not tasks:
            return "📭 您还没有任何任务。"
        
        lines = []
        for t in tasks[:5]:  # Show only 5 most recent tasks
            typ = "🔄循环" if t.type == TaskType.LOOP else "⚡一次"
            lines.append(f"- [{typ}] {t.goal} | {t.status.value} | ID: {t.task_id[:8]}")
        
        return "📋 您的任务列表：\n" + "\n".join(lines)
    
    def execute_task(self, task: Task) -> str:
        """Execute a task"""
        # Simplified implementation
        self.task_repo.update_task(task.task_id, {"status": TaskStatus.RUNNING})
        
        # Simulate task execution
        result = f"✅ 任务已完成：{task.goal}"
        
        self.task_repo.update_task(task.task_id, {
            "status": TaskStatus.COMPLETED,
            "result": result,
            "last_run_time": datetime.now()
        })
        
        return result

# Register the capability
from capabilities.registry import capability_registry
capability_registry.register_class("task_planner", TaskPlannerCapability)
