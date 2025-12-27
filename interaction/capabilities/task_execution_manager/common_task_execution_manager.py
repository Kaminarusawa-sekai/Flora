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
    
    def execute_task(self, request_id: str, draft_id: str, parameters: Dict[str, Any], task_type: str, user_id: str) -> TaskExecutionContextDTO:
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
            request_id=request_id,
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
            external_job_id=None
        )
        
        # 调用外部执行系统
        try:
            # [适配修改] 构造 task_content
            # 新的 Client 需要 task_content 字典来定义具体执行逻辑
            # 如果 parameters 中包含 task_content 则直接使用，否则构造一个默认的
            task_content = parameters.get("task_content", {
                "type": task_type,
                "description": parameters.get("description", "")
            })

            # [适配修改] 使用新的 submit_task 方法
            # 注意：trace_id 是返回值，request_id 是传入参数
            trace_id = self.external_executor.submit_task(
                task_name=task_type,      # 使用 task_type 作为任务名，或者从 parameters 获取 name
                task_content=task_content,
                parameters=parameters,
                user_id=user_id,
                request_id=request_id     # 传入 request_id 以便 client 传递给后端
            )
            
            # 记录外部任务ID (即 trace_id)
            task_context.external_job_id = trace_id

        except Exception as e:
            # 如果提交失败，标记任务为失败
            error_msg = str(e)
            self.logger.error(f"提交任务失败: {error_msg}")
            task_context.execution_status = ExecutionStatus.FAILED
            task_context.error_detail = {"message": error_msg}
        
        return task_context
    
    def stop_task(self, request_id: str):
        """停止任务执行
        
        Args:
            request_id: 请求ID
        """
        # [适配修改] 方法名变为 cancel_task，使用 request_id 参数
        try:
            self.external_executor.cancel_task(request_id=request_id)
        except Exception as e:
            self.logger.error(f"停止任务失败 [request_id={request_id}]: {e}")
    
    def pause_task(self, request_id: str):
        """暂停任务执行
        
        Args:
            request_id: 请求ID
        """
        # [适配修改] 方法名变为 pause_task，使用 request_id 参数
        try:
            self.external_executor.pause_task(request_id=request_id)
        except Exception as e:
            self.logger.error(f"暂停任务失败 [request_id={request_id}]: {e}")
    
    def resume_task(self, request_id: str):
        """恢复任务执行
        
        Args:
            request_id: 请求ID
        """
        # [适配修改] 方法名变为 resume_task，使用 request_id 参数
        try:
            self.external_executor.resume_task(request_id=request_id)
        except Exception as e:
            self.logger.error(f"恢复任务失败 [request_id={request_id}]: {e}")
    
   

    def handle_task_interruption(self, request_id: str, field_name: str, message: str):
        """处理任务中断，等待用户输入
        
        Args:
            request_id: 请求ID  
            field_name: 等待输入的字段名
            message: 中断消息
        """
        # 获取任务上下文
        pass
    
    def resume_interrupted_task(self, request_id: str, input_value: Any):
        """恢复被中断的任务
        
        Args:
            request_id: 请求ID
            input_value: 用户输入的值
        """
        # 获取任务上下文
        pass
            
            # 外部系统负责实际执行，这里无需重新启动
    
    def complete_task(self, request_id: str, result: Dict[str, Any]):
        """完成任务
        
        Args:
            request_id: 请求ID
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
    
    def get_task_status(self, request_id: str) -> Optional[Dict[str, Any]]:
        """获取任务状态
        
        Args:
            request_id: 请求ID
            
        Returns:
            任务状态信息
        """
        external_status = None
        # 如果有外部任务ID，可以调用外部API获取最新状态
        if request_id:
            try:
                # [适配修改] 使用 request_id 参数调用 get_task_status
                # Client 会自动处理 request_id -> trace_id 的解析
                external_status = self.external_executor.get_task_status(request_id=request_id)

            except Exception as e:
                # 如果外部状态获取失败，忽略并继续使用本地状态
                self.logger.warning(f"获取外部任务状态失败 [request_id={request_id}]: {e}")
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
    
    def _on_external_task_completed(self, request_id: str, result: Dict[str, Any]):
        """外部任务完成回调
        
        Args:
            request_id: 请求ID
            result: 任务执行结果
        """
        self.complete_task(request_id, result)
    
    def _on_external_task_failed(self, request_id: str, error: Dict[str, Any]):
        """外部任务失败回调
        
        Args:
            request_id: 请求ID
            error: 错误信息
        """
        self.fail_task(request_id, error)
