from typing import Dict, Any, Optional, List
from .interface import ITaskExecutionManagerCapability
from ...common import (
    TaskExecutionContextDTO,
    ExecutionStatus,
    ExecutionLogEntry
)
from ..llm.interface import ILLMCapability
from interaction.external.client.task_client import TaskClient

class CommonTaskExecution(ITaskExecutionManagerCapability):
    """任务执行管理器 - 负责任务的生命周期协调、外部执行系统交互和状态同步"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务执行管理器"""
        self.config = config
        self._llm = None
        self._external_executor = None
    
    @property
    def llm(self):
        """懒加载LLM能力"""
        if self._llm is None:
            from .. import get_capability
            self._llm = get_capability("llm", expected_type=ILLMCapability)
        return self._llm
    
    @property
    def external_executor(self):
        """懒加载外部任务执行客户端"""
        if self._external_executor is None:
            self._external_executor = TaskClient()
        return self._external_executor
    
    def shutdown(self) -> None:
        """关闭任务执行管理器"""
        # 外部执行系统负责任务生命周期，这里无需特殊处理
        pass
    
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
            error_detail=None,
            external_job_id=None  # 新增：外部任务ID
        )
        
        # 保存任务执行上下文
        self.task_storage.save_execution_context(task_context)
        
        # 添加执行日志
        self._add_log_entry(task_context, "INFO", f"任务 {task_context.task_id} 开始执行")
        
        # 调用外部执行系统
        try:
            external_job_id = self.external_executor.submit(
                task_id=task_context.task_id,
                task_type=task_type,
                parameters=parameters,
                user_id=user_id
            )
            # 记录外部任务ID
            task_context.external_job_id = external_job_id
            self.task_storage.update_execution_context(task_context)
        except Exception as e:
            # 如果提交失败，标记任务为失败
            error_msg = str(e)
            self.fail_task(task_context.task_id, {"message": error_msg})
        
        return task_context
    
    def stop_task(self, task_id: str):
        """停止任务执行
        
        Args:
            task_id: 任务ID
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if not task_context or not task_context.external_job_id:
            return
        
        # 调用外部执行系统停止任务
        self.external_executor.stop(task_context.external_job_id)
    
    def pause_task(self, task_id: str):
        """暂停任务执行
        
        Args:
            task_id: 任务ID
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if not task_context or not task_context.external_job_id:
            return
        
        # 调用外部执行系统暂停任务
        self.external_executor.pause(task_context.external_job_id)
    
    def resume_task(self, task_id: str):
        """恢复任务执行
        
        Args:
            task_id: 任务ID
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if not task_context or not task_context.external_job_id:
            return
        
        # 调用外部执行系统恢复任务
        self.external_executor.resume(task_context.external_job_id)
    
    def retry_task(self, task_id: str):
        """重试任务执行
        
        Args:
            task_id: 任务ID
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if not task_context:
            return
        
        # 调用外部执行系统重试任务
        try:
            new_external_job_id = self.external_executor.retry(
                task_id=task_id,
                task_type=task_context.task_type,
                parameters=task_context.parameters,
                user_id=task_context.created_by
            )
            
            # 更新任务上下文
            task_context.execution_status = ExecutionStatus.RUNNING
            task_context.control_status = "NORMAL"
            task_context.external_job_id = new_external_job_id
            task_context.error_detail = None
            
            # 添加重试日志
            self._add_log_entry(task_context, "INFO", f"任务 {task_id} 开始重试")
            
            # 更新任务上下文
            self.task_storage.update_execution_context(task_context)
        except Exception as e:
            # 如果重试失败，标记任务为失败
            self.fail_task(task_id, {"message": str(e)})
    
    def terminate_task(self, task_id: str):
        """强制终止任务执行
        
        Args:
            task_id: 任务ID
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if not task_context or not task_context.external_job_id:
            return
        
        # 调用外部执行系统强制终止任务
        self.external_executor.terminate(task_context.external_job_id)
    
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
            
            # 外部系统负责实际执行，这里无需重新启动
    
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
    
    def fail_task(self, task_id: str, error: Dict[str, Any]):
        """标记任务失败
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        # 获取任务上下文
        task_context = self.task_storage.get_execution_context(task_id)
        if task_context:
            # 使用LLM生成用户友好的错误提示
            try:
                if self.llm:
                    prompt = f"将以下技术错误转换为用户友好的中文提示（不超过50字）：{error}"
                    user_msg = self.llm.generate_text(prompt).strip()
                    error["user_friendly_message"] = user_msg
            except Exception as e:
                # 如果LLM调用失败，忽略并继续
                pass
            
            # 更新任务状态
            task_context.execution_status = ExecutionStatus.FAILED
            task_context.error_detail = error
            
            # 添加失败日志
            self._add_log_entry(task_context, "ERROR", f"任务 {task_id} 执行失败: {error.get('message', '未知错误')}")
            
            # 更新任务上下文
            self.task_storage.update_execution_context(task_context)
    
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
        # 使用LLM生成更有意义的任务标题
        try:
            if self.llm and "description" in parameters:
                prompt = f"根据任务类型 '{task_type}' 和描述 '{parameters['description']}'，生成一个简洁的任务标题（不超过20字）。"
                title = self.llm.generate_text(prompt).strip()
                return title
        except Exception as e:
            # 如果LLM调用失败，使用默认标题
            pass
        
        # 默认标题生成
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
        
        # 如果有外部任务ID，可以调用外部API获取最新状态
        if task_context.external_job_id:
            try:
                external_status = self.external_executor.get_task_status(task_context.external_job_id)
                if external_status:
                    # 同步外部状态到本地（如果需要）
                    # self._sync_external_status(task_id, external_status)
                    # 更新状态信息
                    status_info["external_status"] = external_status["status"]
                    status_info["progress"] = external_status["progress"]
            except Exception as e:
                # 如果外部状态获取失败，忽略并继续使用本地状态
                pass
        
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
    
    def _on_external_task_completed(self, task_id: str, result: Dict[str, Any]):
        """外部任务完成回调
        
        Args:
            task_id: 任务ID
            result: 任务执行结果
        """
        self.complete_task(task_id, result)
    
    def _on_external_task_failed(self, task_id: str, error: Dict[str, Any]):
        """外部任务失败回调
        
        Args:
            task_id: 任务ID
            error: 错误信息
        """
        self.fail_task(task_id, error)
