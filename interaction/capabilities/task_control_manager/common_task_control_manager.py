from typing import Dict, Any, Optional
from .interface import ITaskControlManagerCapability
from common.task_execution import TaskControlResponseDTO
from common import (
    ExecutionStatus,
    IntentRecognitionResultDTO,
    UserInputDTO
)
from ..llm.interface import ILLMCapability
from external.client import TaskClient

class CommonTaskControl(ITaskControlManagerCapability):
    """任务控制管理器 - 控制任务的执行"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务控制管理器"""
        import logging
        self.config = config
        self._llm: Optional[ILLMCapability] = None
        self.logger = logging.getLogger(__name__)
        # 初始化外部任务客户端
        self.external_task_client = TaskClient()
    @property
    def llm(self) -> ILLMCapability:
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
       
        
    
    def shutdown(self) -> None:
        """关闭任务控制管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "task_control"
    
    # --- 辅助方法：处理外部客户端结果 ---
    def _handle_client_result(self, result: Dict[str, Any], task_id: str, operation: str) -> TaskControlResponseDTO:
        """统一处理 External TaskClient 的返回结果"""
        # 假设 external client 返回的是 {"success": bool, "message": str, ...}
        if result.get("success", False):
            return TaskControlResponseDTO.success_result(
                message=result.get("message", "操作成功"),
                task_id=task_id,
                operation=operation,
                data=result
            )
        else:
            return TaskControlResponseDTO.error_result(
                message=result.get("message", "操作失败"),
                task_id=task_id,
                operation=operation
            )
    
    def cancel_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """取消任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        op = "CANCEL"
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 验证操作合法性
        if task_status["execution_status"] in ["COMPLETED", "CANCELLED"]:
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 已完成或已取消，无法取消", task_id, op)
        
        if not task_status.get("is_cancelable", True):
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不允许取消", task_id, op)
        
        # 3. 执行取消操作
        result = self.external_task_client.cancel_task(task_id)
        return self._handle_client_result(result, task_id, op)
    
    def pause_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """暂停任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        op = "PAUSE"
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 验证操作合法性
        if task_status["execution_status"] not in ["RUNNING", "AWAITING_USER_INPUT"]:
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不在运行状态，无法暂停", task_id, op)
        
        if not task_status["is_resumable"]:
            # 使用LLM生成友好提示
            try:
                prompt = f"""
                用户尝试暂停一个不支持暂停的任务（类型：{task_status['task_type']}，描述：{task_status['description']}）。
                请用中文生成一条不超过50字的友好提示，解释为什么不能暂停，并给出替代建议。
                """
                explanation = self.llm.generate(prompt).strip()
                return TaskControlResponseDTO.error_result(explanation, task_id, op)
            except Exception:
                # 降级到默认消息
                return TaskControlResponseDTO.error_result(f"任务 {task_id} 不支持暂停/恢复", task_id, op)
        
        # 3. 执行暂停操作
        result = self.external_task_client.pause_task(task_id)
        return self._handle_client_result(result, task_id, op)
    
    def resume_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """恢复任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        op = "RESUME"
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 验证操作合法性
        if task_status["control_status"] != "PAUSED":
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 未暂停，无法恢复", task_id, op)
        
        # 3. 执行恢复操作
        result = self.external_task_client.resume_task(task_id)
        return self._handle_client_result(result, task_id, op)
    
    def retry_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """重试任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        op = "RETRY"
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 验证操作合法性
        if task_status["execution_status"] not in ["FAILED", "ERROR"]:
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 未失败，无法重试", task_id, op)
        
        # 3. 执行重试操作
        result = self.external_task_client.retry_task(task_id)
        return self._handle_client_result(result, task_id, op)
    
    def terminate_task(self, task_id: str, user_id: str) -> TaskControlResponseDTO:
        """强制终止任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        op = "TERMINATE"
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return TaskControlResponseDTO.error_result(f"任务 {task_id} 不存在", task_id, op)
        
        # 2. 执行终止操作
        result = self.external_task_client.terminate_task(task_id)
        return self._handle_client_result(result, task_id, op)
    
    def pause_all_tasks(self, user_id: str) -> TaskControlResponseDTO:
        """暂停所有正在运行的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 直接调用外部客户端暂停所有任务
        result = self.external_task_client.pause_all_tasks(user_id)
        # 这里的 task_id 设为 "ALL"
        return self._handle_client_result(result, "ALL", "PAUSE_ALL")
    
    def handle_task_control(self, intent_result: IntentRecognitionResultDTO, user_input: UserInputDTO, user_id: str, dialog_state: Any, last_mentioned_task_id: Optional[str] = None) -> TaskControlResponseDTO:
        """处理任务控制意图
        
        Args:
            intent_result: 意图识别结果
            user_input: 原始用户输入
            user_id: 用户ID
            dialog_state: 对话状态上下文
            last_mentioned_task_id: 上次提到的任务ID
            
        Returns:
            操作结果
        """
        # 1. 从实体中提取任务ID
        task_id = None
        for entity in intent_result.entities:
            if entity.name == "task_id":
                task_id = entity.resolved_value or entity.value
                break
        
        # 2. 如果没有提取到任务ID，使用上次提到的任务ID
        if not task_id:
            task_id = last_mentioned_task_id
        
        # 3. 如果仍然没有任务ID，尝试根据上下文和输入推断
        if not task_id:
            task_id = self._infer_task_id(intent_result, user_input, user_id, dialog_state)
        
        if not task_id:
            return TaskControlResponseDTO.error_result(
                message="请指定要操作的任务ID",
                operation="UNKNOWN"
            )
        
        # 4. 根据意图类型调用相应的任务控制方法
        intent_type = intent_result.primary_intent
        
        if intent_type == "DELETE" or intent_type == "CANCEL":
            return self.cancel_task(task_id, user_id)
        elif intent_type == "PAUSE":
            return self.pause_task(task_id, user_id)
        elif intent_type == "RESUME_TASK":
            return self.resume_task(task_id, user_id)
        elif intent_type == "RETRY":
            return self.retry_task(task_id, user_id)
        else:
            return TaskControlResponseDTO.error_result(
                message=f"不支持的任务控制意图类型: {intent_type}",
                task_id=task_id,
                operation="UNKNOWN"
            )
    
    def _infer_task_id(self, intent_result: IntentRecognitionResultDTO, user_input: UserInputDTO, user_id: str, dialog_state: Any) -> Optional[str]:
        """根据上下文、输入和任务列表推断任务ID
        
        Args:
            intent_result: 意图识别结果
            user_input: 原始用户输入
            user_id: 用户ID
            dialog_state: 对话状态上下文
            
        Returns:
            推断出的任务ID，或者None
        """
        try:
            # 1. 获取所有正在执行的任务
            running_tasks_result = self.external_task_client.get_running_tasks(user_id)
            running_tasks = running_tasks_result.get("tasks", [])
            
            # 2. 从对话状态中获取最近的任务ID作为参考
            recent_task_id = None
            if hasattr(dialog_state, 'recent_tasks') and dialog_state.recent_tasks:
                recent_task_id = dialog_state.recent_tasks[-1].task_id
            
            # 3. 如果有正在执行的任务，使用大模型智能判断
            if running_tasks:
                # 构建任务列表描述
                tasks_description = "\n".join([
                    f"任务ID: {task['task_id']}, 类型: {task['task_type']}, 描述: {task['description']}, 状态: {task['execution_status']}"
                    for task in running_tasks
                ])
                
                prompt = f"""
                用户输入：{user_input.utterance}
                用户ID：{user_id}
                最近操作的任务ID：{recent_task_id if recent_task_id else '无'}
                
                以下是当前正在执行的任务列表：
                {tasks_description}
                
                请仔细分析用户的输入，判断用户想要操作的是哪个任务？
                
                要求：
                1. 只输出任务ID，如果无法判断或没有匹配的任务，请输出"NONE"
                2. 只输出结果，不要有任何解释
                3. 如果用户明确提到某个任务ID，请优先匹配
                4. 如果没有明确提到任务ID，请根据任务类型、描述和用户输入的关联性进行判断
                5. 如果用户输入是通用指令（如"暂停所有任务"），请输出"ALL"
                """
                
                llm_result = self.llm.generate(prompt).strip()
                
                # 处理大模型返回结果
                if llm_result and llm_result != "NONE" and llm_result != "ALL":
                    # 验证返回的任务ID是否确实在正在执行的任务列表中
                    for task in running_tasks:
                        if task["task_id"] == llm_result:
                            return llm_result
            
            # 如果没有正在执行的任务或大模型无法判断，返回None
            return None
        except Exception as e:
            self.logger.error(f"Failed to infer task ID: {e}")
            return None