from typing import Dict, Any, Optional
from .interface import ITaskControlManager
from ...common import (
    TaskExecutionContextDTO,
    ExecutionStatus,
    IntentRecognitionResultDTO
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonTaskControlManager(ITaskControlManager):
    """任务控制管理器 - 控制任务的执行"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务控制管理器"""
        self.config = config
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
    
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
        # 1. 获取任务执行上下文
        task = self.task_storage.get_execution_context(task_id)
        if not task:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 验证操作合法性
        if task.control_status in ["COMPLETED", "CANCELLED"]:
            return {"success": False, "message": f"任务 {task_id} 已完成或已取消，无法取消"}
        
        if not task.is_cancelable:
            return {"success": False, "message": f"任务 {task_id} 不允许取消"}
        
        # 3. 执行取消操作
        task.execution_status = ExecutionStatus.CANCELLED
        task.control_status = "CANCELLED_BY_USER"
        
        # 4. 更新任务状态
        self.task_storage.update_execution_context(task)
        
        # 5. 通知执行管理器停止任务
        if self.task_execution_manager:
            self.task_execution_manager.stop_task(task_id)
        
        return {"success": True, "message": f"任务 {task_id} 已成功取消"}
    
    def pause_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """暂停任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务执行上下文
        task = self.task_storage.get_execution_context(task_id)
        if not task:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 验证操作合法性
        if task.execution_status not in [ExecutionStatus.RUNNING, ExecutionStatus.AWAITING_USER_INPUT]:
            return {"success": False, "message": f"任务 {task_id} 不在运行状态，无法暂停"}
        
        if not task.is_resumable:
            return {"success": False, "message": f"任务 {task_id} 不支持暂停/恢复"}
        
        # 3. 执行暂停操作
        task.control_status = "PAUSED"
        
        # 4. 更新任务状态
        self.task_storage.update_execution_context(task)
        
        # 5. 通知执行管理器暂停任务
        if self.task_execution_manager:
            self.task_execution_manager.pause_task(task_id)
        
        return {"success": True, "message": f"任务 {task_id} 已成功暂停"}
    
    def resume_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """恢复任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务执行上下文
        task = self.task_storage.get_execution_context(task_id)
        if not task:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 验证操作合法性
        if task.control_status != "PAUSED":
            return {"success": False, "message": f"任务 {task_id} 未暂停，无法恢复"}
        
        # 3. 执行恢复操作
        task.control_status = "NORMAL"
        task.execution_status = ExecutionStatus.RUNNING
        
        # 4. 更新任务状态
        self.task_storage.update_execution_context(task)
        
        # 5. 通知执行管理器恢复任务
        if self.task_execution_manager:
            self.task_execution_manager.resume_task(task_id)
        
        return {"success": True, "message": f"任务 {task_id} 已成功恢复"}
    
    def retry_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """重试任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务执行上下文
        task = self.task_storage.get_execution_context(task_id)
        if not task:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 验证操作合法性
        if task.execution_status not in [ExecutionStatus.FAILED, ExecutionStatus.ERROR]:
            return {"success": False, "message": f"任务 {task_id} 未失败，无法重试"}
        
        # 3. 重置任务状态
        task.execution_status = ExecutionStatus.NOT_STARTED
        task.control_status = "NORMAL"
        task.error_detail = None
        
        # 4. 更新任务状态
        self.task_storage.update_execution_context(task)
        
        # 5. 通知执行管理器重新执行任务
        if self.task_execution_manager:
            self.task_execution_manager.retry_task(task_id)
        
        return {"success": True, "message": f"任务 {task_id} 已成功重试"}
    
    def terminate_task(self, task_id: str, user_id: str) -> Dict[str, Any]:
        """强制终止任务
        
        Args:
            task_id: 任务ID
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取任务执行上下文
        task = self.task_storage.get_execution_context(task_id)
        if not task:
            return {"success": False, "message": f"任务 {task_id} 不存在"}
        
        # 2. 执行终止操作
        task.execution_status = ExecutionStatus.FAILED
        task.control_status = "TERMINATED"
        
        # 3. 更新任务状态
        self.task_storage.update_execution_context(task)
        
        # 4. 通知执行管理器终止任务
        if self.task_execution_manager:
            self.task_execution_manager.terminate_task(task_id)
        
        return {"success": True, "message": f"任务 {task_id} 已成功终止"}
    
    def pause_all_tasks(self, user_id: str) -> Dict[str, Any]:
        """暂停所有正在运行的任务
        
        Args:
            user_id: 用户ID
            
        Returns:
            操作结果
        """
        # 1. 获取所有正在运行的任务
        tasks = self.task_storage.list_execution_contexts(user_id, {"status": "RUNNING"})
        
        # 2. 逐个暂停任务
        success_count = 0
        failed_count = 0
        
        for task in tasks:
            result = self.pause_task(task.task_id, user_id)
            if result["success"]:
                success_count += 1
            else:
                failed_count += 1
        
        return {
            "success": True,
            "message": f"已成功暂停 {success_count} 个任务，{failed_count} 个任务暂停失败"
        }