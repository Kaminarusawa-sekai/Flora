from typing import Dict, Any, Optional, List
from .interface import ITaskExecutionManager
from ...common import (
    TaskExecutionContextDTO,
    ExecutionStatus,
    ExecutionLogEntry
)
from tasks.capabilities import get_capability
from tasks.capabilities.llm.interface import ILLMCapability

class CommonTaskExecutionManager(ITaskExecutionManager):
    """任务执行管理器 - 负责任务的实际执行、中断处理和状态更新"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务执行管理器"""
        self.config = config
        # 这里可以初始化任务执行池或工作线程
        # 获取LLM能力
        self.llm = get_capability("llm", expected_type=ILLMCapability)
        # 初始化运行任务字典
        self.running_tasks = {}
    
    def shutdown(self) -> None:
        """关闭任务执行管理器"""
        # 关闭所有正在运行的任务
        for task_id in list(self.running_tasks.keys()):
            self.stop_task(task_id)
    
    def get_capability_type(self) -> str:
        """返回能力类型"""
        return "task_execution"
    
    def execute_task(self, draft_id: str, parameters: Dict[str, Any], task_type: str, user_id: str) -> TaskExecutionContextDTO:
        """执行任务
        
        Args:
            draft_id: 关联的草稿ID
            parameters: 执行参数
            task_type: 任务类型
            user_id: 用户ID
            
        Returns:
            任务执行上下文DTO
        """
        # 创建任务执行上下文
        task_context = TaskExecutionContextDTO(
            draft_id=draft_id,
            task_type=task_type,
            parameters=parameters,
            execution_status=ExecutionStatus.RUNNING,
            awaiting_input_for=None,
            interruption_message=None,
            last_checkpoint=None,
            schedule=None,
            control_status="NORMAL",
            parent_task_id=None,
            run_index=None,
            title=self._generate_task_title(task_type, parameters),
            tags=self._generate_task_tags(task_type),
            created_by=user_id,
            logs=[],
            result_data=None,
            error_detail=None
        )
        
        # 保存任务执行上下文
        self.task_storage.save_execution_context(task_context)
        
        # 添加执行日志
        self._add_log_entry(task_context, "INFO", f"任务 {task_context.task_id} 开始执行")
        
        # 启动任务执行（异步）
        self._start_task_execution(task_context)
        
        return task_context
    
    def _start_task_execution(self, task_context: TaskExecutionContextDTO):
        """启动任务执行（异步）
        
        Args:
            task_context: 任务执行上下文DTO
        """
        # 这里简化实现，实际应该使用线程池或异步任务队列
        # 示例：模拟任务执行
        task_id = task_context.task_id
        self.running_tasks[task_id] = True
        
        # 模拟任务执行过程
        # 实际应该调用具体的任务处理器
        
    def stop_task(self, task_id: str):
        """停止任务执行
        
        Args:
            task_id: 任务ID
        """
        if task_id in self.running_tasks:
            del self.running_tasks[task_id]
    
    def pause_task(self, task_id: str):
        """暂停任务执行
        
        Args:
            task_id: 任务ID
        """
        # 实现任务暂停逻辑
        pass
    
    def resume_task(self, task_id: str):
        """恢复任务执行
        
        Args:
            task_id: 任务ID
        """
        # 实现任务恢复逻辑
        pass
    
    def retry_task(self, task_id: str):
        """重试任务执行
        
        Args:
            task_id: 任务ID
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if task_context:
            # 重置任务状态
            task_context.execution_status = ExecutionStatus.RUNNING
            task_context.control_status = "NORMAL"
            
            # 添加重试日志
            self._add_log_entry(task_context, "INFO", f"任务 {task_id} 开始重试")
            
            # 重新启动任务执行
            self._start_task_execution(task_context)
    
    def terminate_task(self, task_id: str):
        """强制终止任务执行
        
        Args:
            task_id: 任务ID
        """
        # 实现任务强制终止逻辑
        self.stop_task(task_id)
    
    def handle_task_interruption(self, task_id: str, field_name: str, message: str):
        """处理任务中断，等待用户输入
        
        Args:
            task_id: 任务ID
            field_name: 等待输入的字段名
            message: 中断消息
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if task_context:
            # 更新任务状态
            task_context.execution_status = ExecutionStatus.AWAITING_USER_INPUT
            task_context.awaiting_input_for = field_name
            task_context.interruption_message = message
            
            # 添加中断日志
            self._add_log_entry(task_context, "INFO", f"任务 {task_id} 中断，等待用户输入: {field_name}")
            
            # 更新任务上下文
            self.task_storage.update_execution_context(task_context)
    
    def resume_interrupted_task(self, task_id: str, input_value: Any):
        """恢复被中断的任务
        
        Args:
            task_id: 任务ID
            input_value: 用户输入的值
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if task_context and task_context.execution_status == ExecutionStatus.AWAITING_USER_INPUT:
            # 更新任务状态
            task_context.execution_status = ExecutionStatus.RUNNING
            task_context.parameters[task_context.awaiting_input_for] = input_value
            task_context.awaiting_input_for = None
            task_context.interruption_message = None
            
            # 添加恢复日志
            self._add_log_entry(task_context, "INFO", f"任务 {task_id} 恢复执行")
            
            # 更新任务上下文
            self.task_storage.update_execution_context(task_context)
            
            # 重新启动任务执行
            self._start_task_execution(task_context)
    
    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """完成任务
        
        Args:
            task_id: 任务ID
            result: 任务执行结果
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if task_context:
            # 更新任务状态
            task_context.execution_status = ExecutionStatus.COMPLETED
            task_context.result_data = result
            
            # 添加完成日志
            self._add_log_entry(task_context, "INFO", f"任务 {task_id} 执行完成")
            
            # 更新任务上下文
            self.task_storage.update_execution_context(task_context)
            
            # 移除正在运行的任务
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def fail_task(self, task_id: str, error: Dict[str, Any]):
        """标记任务失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if task_context:
            # 更新任务状态
            task_context.execution_status = ExecutionStatus.FAILED
            task_context.error_detail = error
            
            # 添加失败日志
            self._add_log_entry(task_context, "ERROR", f"任务 {task_id} 执行失败: {error.get('message', '未知错误')}")
            
            # 更新任务上下文
            self.task_storage.update_execution_context(task_context)
            
            # 移除正在运行的任务
            if task_id in self.running_tasks:
                del self.running_tasks[task_id]
    
    def _add_log_entry(self, task_context: TaskExecutionContextDTO, level: str, message: str):
        """添加日志条目
        
        Args:
            task_context: 任务执行上下文DTO
            level: 日志级别
            message: 日志消息
        """
        log_entry = ExecutionLogEntry(
            level=level,
            message=message
        )
        task_context.logs.append(log_entry)
    
    def _generate_task_title(self, task_type: str, parameters: Dict[str, Any]) -> str:
        """生成任务标题
        
        Args:
            task_type: 任务类型
            parameters: 执行参数
            
        Returns:
            任务标题
        """
        # 简化的标题生成，实际应该根据任务类型和参数生成更有意义的标题
        if "task_name" in parameters:
            return parameters["task_name"]
        return f"{task_type} 任务"
    
    def _generate_task_tags(self, task_type: str) -> List[str]:
        """生成任务标签
        
        Args:
            task_type: 任务类型
            
        Returns:
            任务标签列表
        """
        # 根据任务类型生成标签
        return [task_type.lower()]
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if not task_context:
            return None
        
        # 生成状态信息
        status_info = {
            "task_id": task_context.task_id,
            "status": task_context.execution_status,
            "control_status": task_context.control_status,
            "title": task_context.title,
            "progress": self._calculate_task_progress(task_context),
            "last_log": task_context.logs[-1].message if task_context.logs else None
        }
        
        return status_info
    
    def _calculate_task_progress(self, task_context: TaskExecutionContextDTO) -> float:
        """计算任务进度
        
        Args:
            task_context: 任务执行上下文DTO
            
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
        
        return status_progress_map.get(task_context.execution_status, 0.0)