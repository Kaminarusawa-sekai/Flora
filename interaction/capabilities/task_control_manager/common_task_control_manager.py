from typing import Dict, Any, Optional
from .interface import ITaskControlManagerCapability
from ...common import (
    ExecutionStatus,
    IntentRecognitionResultDTO
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability
from interaction.external.client.task_execution_client import TaskExecutionClient

class CommonTaskControl(ITaskControlManagerCapability):
    """任务控制管理器 - 控制任务的执行"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务控制管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
        # 初始化外部任务执行客户端
        self.external_task_client = TaskExecutionClient()
    
    def shutdown(self) -> None:
        """关闭任务控制管理器"""
        pass
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "task_control"
    
    def cancel_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """取消任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 验证操作合法性
        if task_status["control_status"] in ["COMPLETED", "CANCELLED"]:
            return {"success": False, "message": f"任务 {task_id} 已完成或已取消，无法取消"}
        
        if not task_status["is_cancelable"]:
            # 使用LLM生成友好提示
            try:
                prompt = f"""
                用户尝试取消一个不允许取消的任务（类型：{task_status['task_type']}，描述：{task_status['description']}）。
                请用中文生成一条不超过50字的友好提示，解释为什么不能取消，并给出替代建议。
                """
                explanation = self.llm.generate_text(prompt).strip()
                return {"success": False, "message": explanation}
            except Exception as e:
                # 降级到默认消息
                return {"success": False, "message": f"任务 {task_id} 不允许取消"}
        
        # 3. 执行取消操作
        result = self.external_task_client.cancel_task(task_id)
        
        # 4. 通知执行管理器停止任务（如果需要）
        if self.task_execution_manager:
            self.task_execution_manager.stop_task(task_id)
        
        return result
    
    def pause_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """暂停任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 验证操作合法性
        if task_status["execution_status"] not in ["RUNNING", "AWAITING_USER_INPUT"]:
            return {"success": False, "message": f"任务 {task_id} 不在运行状态，无法暂停"}
        
        if not task_status["is_resumable"]:
            # 使用LLM生成友好提示
            try:
                prompt = f"""
                用户尝试暂停一个不支持暂停的任务（类型：{task_status['task_type']}，描述：{task_status['description']}）。
                请用中文生成一条不超过50字的友好提示，解释为什么不能暂停，并给出替代建议。
                """
                explanation = self.llm.generate_text(prompt).strip()
                return {"success": False, "message": explanation}
            except Exception as e:
                # 降级到默认消息
                return {"success": False, "message": f"任务 {task_id} 不支持暂停/恢复"}
        
        # 3. 执行暂停操作
        result = self.external_task_client.pause_task(task_id)
        
        # 4. 通知执行管理器暂停任务（如果需要）
        if self.task_execution_manager:
            self.task_execution_manager.pause_task(task_id)
        
        return result
    
    def resume_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """恢复任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 验证操作合法性
        if task_status["control_status"] != "PAUSED":
            return {"success": False, "message": f"任务 {task_id} 未暂停，无法恢复"}
        
        # 3. 执行恢复操作
        result = self.external_task_client.resume_task(task_id)
        
        # 4. 通知执行管理器恢复任务（如果需要）
        if self.task_execution_manager:
            self.task_execution_manager.resume_task(task_id)
        
        return result
    
    def retry_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """重试任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 验证操作合法性
        if task_status["execution_status"] not in ["FAILED", "ERROR"]:
            return {"success": False, "message": f"任务 {task_id} 未失败，无法重试"}
        
        # 3. 执行重试操作
        result = self.external_task_client.retry_task(task_id)
        
        # 4. 通知执行管理器重新执行任务（如果需要）
        if self.task_execution_manager:
            self.task_execution_manager.retry_task(task_id)
        
        return result
    
    def terminate_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """强制终止任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务状态
        task_status = self.external_task_client.get_task_status(task_id)
        if not task_status:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 执行终止操作
        result = self.external_task_client.terminate_task(task_id)
        
        # 3. 通知执行管理器终止任务（如果需要）
        if self.task_execution_manager:
            self.task_execution_manager.terminate_task(task_id)
        
        return result
    
    def pause_all_tasks(self, user_id: str) -> Dict[str, Any]:
        """暂停所有正在运行的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 直接调用外部客户端暂停所有任务
        result = self.external_task_client.pause_all_tasks(user_id)
        
        return result