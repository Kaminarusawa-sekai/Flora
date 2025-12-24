from typing import Dict, Any, Optional, List
from .interface import ITaskExecutionManagerCapability
from common import (
    TaskExecutionContextDTO,
    ExecutionStatus,
    ExecutionLogEntry
)
from ..llm.interface import ILLMCapability
from external.client.task_client import TaskClient

class CommonTaskExecution(ITaskExecutionManagerCapability):
    """任务执行管理器 - 负责任务的生命周期协调、外部执行系统交互和状态同步"""
    
    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化任务执行管理器"""
        self.logger.info("初始化任务执行管理器")
        self.config = config
        self._llm = None
        self._external_executor = None
        self.logger.info("任务执行管理器初始化完成")
    
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

        
        # 调用外部执行系统停止任务
        self.external_executor.stop(task_id)
    
    def pause_task(self, task_id: str):
        """暂停任务执行
        
        Args:
            task_id: 任务ID
        """
        # 获取任务上下文
        
        # 调用外部执行系统暂停任务
        self.external_executor.pause(task_id)
    
    def resume_task(self, task_id: str):
        """恢复任务执行
        
        Args:
            task_id: 任务ID
        """

        # 调用外部执行系统恢复任务
        self.external_executor.resume(task_id)
    
   

    def handle_task_interruption(self, task_id: str, field_name: str, message: str):
        """处理任务中断，等待用户输入
        
        Args:
            task_id: 任务ID
            field_name: 等待输入的字段名
            message: 中断消息
        """
        # 获取任务上下文
        pass
    
    def resume_interrupted_task(self, task_id: str, input_value: Any):
        """恢复被中断的任务
        
        Args:
            task_id: 任务ID
            input_value: 用户输入的值
        """
        # 获取任务上下文
        pass
            
            # 外部系统负责实际执行，这里无需重新启动
    
    def complete_task(self, task_id: str, result: Dict[str, Any]):
        """完成任务
        
        Args:
            task_id: 任务ID
            result: 任务执行结果
        """
        pass
    
    
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

        # 如果有外部任务ID，可以调用外部API获取最新状态
        if task_id:
            try:
                external_status = self.external_executor.get_task_status(task_id)

                    # 同步外部状态到本地（如果需要）
                    # self._sync_external_status(task_id, external_status)
                    # 更新状态信息

            except Exception as e:
                # 如果外部状态获取失败，忽略并继续使用本地状态
                pass
        
        return external_status
    
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
