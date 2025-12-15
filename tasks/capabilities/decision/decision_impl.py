from typing import Dict, Any
from .interface import ITaskStrategyCapability, ITaskOperationCapability
from ..llm.interface import ILLMCapability



class TaskStrategyCapability(ITaskStrategyCapability):
    """任务策略判断能力实现"""
    
    def __init__(self):
        self.llm = None
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化任务策略判断能力
        
        Args:
            config: 配置参数
        """
        from ..llm.interface import ILLMCapability
        from ..registry import capability_registry
        self.llm = capability_registry.get_capability("llm", ILLMCapability)

        self.llm.initialize({})
    
    def shutdown(self) -> None:
        """
        关闭任务策略判断能力
        """
        if self.llm:
            self.llm.shutdown()
    
    def get_capability_type(self) -> str:
        """
        返回能力类型
        """
        return "decision"
    
    def decide_task_strategy(self, task_desc: str, context: str) -> Dict[str, Any]:
        """
        使用LLM判断任务策略
        """
        prompt = f"""你是一个智能任务分析器。请根据以下信息判断任务的两个属性：

                【当前任务描述】
                {task_desc}

                【相关记忆与上下文】
                {context}

                请严格按以下 JSON 格式输出，不要包含任何额外内容：
                {{
                "is_loop": false,
                "is_parallel": false,
                "reasoning": "简要说明判断依据"
                }}
                """

        try:
            result = self.llm.generate(prompt, parse_json=True, max_tokens=300)

            # 确保字段存在且类型正确
            return {
                "is_loop": bool(result.get("is_loop", False)),
                "is_parallel": bool(result.get("is_parallel", False)),
                "reasoning": str(result.get("reasoning", "No reasoning provided."))
            }

        except Exception as e:
            # 安全回退
            return {
                "is_loop": False,
                "is_parallel": False,
                "reasoning": f"Failed to analyze due to error: {str(e)}. Using default strategy."
            }


class TaskOperationCapability(ITaskOperationCapability):
    """任务操作分类能力实现"""
    
    def __init__(self):
        self.llm = None
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """
        初始化任务操作分类能力
        
        Args:
            config: 配置参数
        """
        from ..llm.interface import ILLMCapability
        from ..registry import capability_registry
        self.llm = capability_registry.get_capability("llm", ILLMCapability)
        self.llm.initialize({})
    
    def shutdown(self) -> None:
        """
        关闭任务操作分类能力
        """
        if self.llm:
            self.llm.shutdown()
    
    def get_capability_type(self) -> str:
        """
        返回能力类型
        """
        return "decision"
    
    def classify_task_operation(self, user_input: str, intent: Any = None) -> str:
        """
        使用LLM判断具体的任务操作
        """
        prompt = f"""你是一个智能任务操作系统。请分析用户当前输入是对任务的具体操作类型。

            【用户输入】
            {user_input}

            系统支持以下任务操作：
            1. new_task: 创建新任务（如“帮我查一下天气”）
            2. comment_on_task: 对已有任务追加评论（如“刚才那个报告太简略了”、“漏了第三点”）
            3. revise_result: 修订任务结果（如“把‘成功’改成‘部分成功’”、“更新数据为100”）
            4. re_run_task: 重新执行任务（如“再试一次”、“重新跑一下”）
            5. cancel_task: 取消任务（如“不用做了”）
            6. archive_task: 归档任务（如“这个可以关了”）
            7. trigger_existing: 立即触发循环任务（如“现在执行日报”）
            8. modify_loop_interval: 修改循环任务间隔（如“改成每天执行”）
            9. pause_loop: 暂停循环任务（如“暂停日报”）
            10. resume_loop: 恢复循环任务（如“恢复日报”）

            请输出严格 JSON：
            {{
            "operation_type": "...",
            "comment_text": "仅 comment_on_task 时存在",
            "revision_content": "仅 revise_result 时存在",
            "reasoning": "..."
            }}

            operation_type 必须是上述之一。
            """

        try:
            response = self.llm.generate(prompt, parse_json=True, max_tokens=300, temperature=0.2)
            
            # 安全转换
            operation_type = response.get("operation_type", "new_task")
            
            # 根据操作类型返回对应的操作码
            if operation_type in ["trigger_existing", "modify_loop_interval", "pause_loop", "resume_loop", "loop_task"]:
                return "LOOP_TASK"
            elif operation_type == "new_task":
                return "NEW_TASK"
            else:
                return operation_type
        except Exception as e:
            return "NEW_TASK"