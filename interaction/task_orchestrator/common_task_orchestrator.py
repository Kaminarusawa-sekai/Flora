"""任务协调器实现"""
import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime
from interaction.task_orchestrator.interface import ITaskOrchestratorCapability
from interaction.common.models import Task, TaskSpec, TaskLog, ClarificationRequest
from events.event_bus import event_bus
from events.event_types import EventType


class CommonTaskOrchestrator(ITaskOrchestratorCapability):
    """任务协调器实现"""
    
    def __init__(self):
        super().__init__()
        # 任务存储（内存实现，实际项目中应使用数据库）
        self._tasks: Dict[str, Task] = {}
        # 会话与任务的映射
        self._session_tasks: Dict[str, List[str]] = {}
        # 任务执行器适配器
        self._executor_adapter = None
    
    def initialize(self):
        """初始化任务协调器"""
        self._load_executor_adapter()
        self.logger.info("✓ Task Orchestrator initialized successfully")
    
    def _load_executor_adapter(self):
        """加载任务执行器适配器"""
        # 这里应该通过依赖注入或配置加载执行器适配器
        # 暂时使用模拟实现
        self._executor_adapter = MockExecutorAdapter()
    
    def execute_task(self, task_spec: TaskSpec, session_id: str, user_id: str = "default_user") -> Dict[str, Any]:
        """
        执行任务
        """
        # 创建任务
        task_id = f"task_{uuid.uuid4().hex[:12]}"
        
        # 初始化任务
        task = Task(
            task_id=task_id,
            draft_id="",  # 暂时为空，后续可以关联草稿
            status="running",
            logs=[TaskLog(step="init", message=f"Task {task_id} created for {task_spec.task_type}")]
        )
        
        # 存储任务
        self._tasks[task_id] = task
        
        # 关联会话
        if session_id not in self._session_tasks:
            self._session_tasks[session_id] = []
        self._session_tasks[session_id].append(task_id)
        
        # 发布任务创建事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_CREATED.value,
            source="TaskOrchestrator",
            agent_id="",
            data={"task_spec": task_spec.to_dict()}
        )
        
        # 执行任务
        try:
            executor_response = self._executor_adapter.execute(
                task_id=task_id,
                task_spec=task_spec.to_dict()
            )
            
            # 处理执行器响应
            return self.handle_executor_response(task_id, executor_response)
            
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {e}")
            task.status = "failed"
            task.error = str(e)
            task.logs.append(TaskLog(step="error", message=str(e), level="error"))
            
            # 发布任务失败事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.TASK_FAILED.value,
                source="TaskOrchestrator",
                agent_id="",
                data={"error": str(e)}
            )
            
            return {
                "task_id": task_id,
                "status": "failed"
            }
    
    def parse_intent_to_task_spec(self, session_id: str, user_message: str) -> Dict[str, Any]:
        """
        解析用户意图为TaskSpec
        """
        # 这里应该调用意图解析器来生成TaskSpec
        # 暂时返回模拟数据
        return {
            "task_spec": TaskSpec(
                task_type="send_email",
                params={
                    "to": "default@example.com",
                    "subject": "Test Email",
                    "body": "This is a test email"
                }
            ),
            "clarification_needed": False,
            "clarification_request": None
        }
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        获取任务信息
        """
        return self._tasks.get(task_id)
    
    def get_tasks_by_session(self, session_id: str) -> List[Task]:
        """
        获取会话关联的所有任务
        """
        task_ids = self._session_tasks.get(session_id, [])
        return [self._tasks[task_id] for task_id in task_ids if task_id in self._tasks]
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        取消任务
        """
        if task_id not in self._tasks:
            return {
                "task_id": task_id,
                "status": "error",
                "error": "Task not found"
            }
        
        task = self._tasks[task_id]
        task.status = "cancelled"
        task.logs.append(TaskLog(step="cancel", message="Task cancelled by user"))
        
        # 通知执行器取消任务
        if self._executor_adapter:
            self._executor_adapter.cancel(task_id)
        
        # 发布任务取消事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_CANCELLED.value,
            source="TaskOrchestrator",
            agent_id="",
            data={}
        )
        
        return {
            "task_id": task_id,
            "status": "cancelled"
        }
    
    def pause_task(self, task_id: str) -> Dict[str, Any]:
        """
        暂停任务
        """
        if task_id not in self._tasks:
            return {
                "task_id": task_id,
                "status": "error",
                "error": "Task not found"
            }
        
        task = self._tasks[task_id]
        task.status = "paused"
        task.logs.append(TaskLog(step="pause", message="Task paused by user"))
        
        # 通知执行器暂停任务
        if self._executor_adapter:
            self._executor_adapter.pause(task_id)
        
        # 发布任务暂停事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_PAUSED.value,
            source="TaskOrchestrator",
            agent_id="",
            data={}
        )
        
        return {
            "task_id": task_id,
            "status": "paused"
        }
    
    def resume_task(self, task_id: str, resume_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        恢复任务
        """
        if task_id not in self._tasks:
            return {
                "task_id": task_id,
                "status": "error",
                "error": "Task not found"
            }
        
        task = self._tasks[task_id]
        task.status = "running"
        task.logs.append(TaskLog(step="resume", message="Task resumed with input"))
        
        # 通知执行器恢复任务
        if self._executor_adapter:
            executor_response = self._executor_adapter.resume(
                task_id=task_id,
                resume_input=resume_input
            )
            return self.handle_executor_response(task_id, executor_response)
        
        # 发布任务恢复事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_RESUMED.value,
            source="TaskOrchestrator",
            agent_id="",
            data={"resume_input": resume_input}
        )
        
        return {
            "task_id": task_id,
            "status": "running"
        }
    
    def retry_task(self, task_id: str) -> Dict[str, Any]:
        """
        重试任务
        """
        if task_id not in self._tasks:
            return {
                "task_id": task_id,
                "status": "error",
                "error": "Task not found"
            }
        
        # 获取原任务
        original_task = self._tasks[task_id]
        
        # 创建新任务
        new_task_id = f"task_{uuid.uuid4().hex[:12]}"
        new_task = Task(
            task_id=new_task_id,
            draft_id=original_task.draft_id,
            status="running",
            logs=[TaskLog(step="init", message=f"Retried task from {task_id}")]
        )
        
        # 存储新任务
        self._tasks[new_task_id] = new_task
        
        # 发布任务重试事件
        event_bus.publish_task_event(
            task_id=new_task_id,
            event_type=EventType.TASK_RETRIED.value,
            source="TaskOrchestrator",
            agent_id="",
            data={"original_task_id": task_id}
        )
        
        # 执行新任务
        try:
            # 这里应该重新获取任务规格
            # 暂时使用模拟数据
            task_spec = TaskSpec(
                task_type="send_email",
                params={
                    "to": "default@example.com",
                    "subject": "Test Email",
                    "body": "This is a test email"
                }
            )
            
            executor_response = self._executor_adapter.execute(
                task_id=new_task_id,
                task_spec=task_spec.to_dict()
            )
            
            return self.handle_executor_response(new_task_id, executor_response)
            
        except Exception as e:
            self.logger.error(f"Error retrying task {new_task_id}: {e}")
            new_task.status = "failed"
            new_task.error = str(e)
            new_task.logs.append(TaskLog(step="error", message=str(e), level="error"))
            
            return {
                "task_id": new_task_id,
                "status": "failed"
            }
    
    def request_task_input(self, task_id: str, field: str, prompt: str, input_type: str = "text", 
                          options: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        请求任务输入
        """
        if task_id not in self._tasks:
            return {
                "status": "error",
                "error": "Task not found"
            }
        
        # 更新任务状态
        task = self._tasks[task_id]
        task.status = "awaiting_input"
        task.current_step = field
        task.logs.append(TaskLog(step="awaiting_input", message=f"Waiting for input: {field}"))
        
        # 创建澄清请求
        clarification_request = ClarificationRequest(
            session_id="",  # 后续需要关联会话
            task_id=task_id,
            field=field,
            prompt=prompt,
            input_type=input_type,
            options=options
        )
        
        # 发布任务等待输入事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_AWAITING_INPUT.value,
            source="TaskOrchestrator",
            agent_id="",
            data={"field": field, "prompt": prompt}
        )
        
        return {
            "status": "awaiting_input",
            "clarification_request": clarification_request
        }
    
    def handle_executor_response(self, task_id: str, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理任务执行器的响应
        """
        if task_id not in self._tasks:
            return {
                "task_id": task_id,
                "status": "error",
                "error": "Task not found"
            }
        
        task = self._tasks[task_id]
        status = response.get("status")
        
        if status == "completed":
            # 任务完成
            task.status = "completed"
            task.result = response.get("result", {})
            task.logs.append(TaskLog(step="completed", message="Task execution completed"))
            
            # 发布任务完成事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.TASK_COMPLETED.value,
                source="TaskOrchestrator",
                agent_id="",
                data={"result": task.result}
            )
            
        elif status == "awaiting_input":
            # 需要输入
            field = response.get("requiredField")
            prompt = response.get("prompt")
            
            return self.request_task_input(task_id, field, prompt)
            
        elif status == "failed":
            # 任务失败
            task.status = "failed"
            task.error = response.get("error", "Unknown error")
            task.logs.append(TaskLog(step="failed", message=task.error, level="error"))
            
            # 发布任务失败事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.TASK_FAILED.value,
                source="TaskOrchestrator",
                agent_id="",
                data={"error": task.error}
            )
        
        return {
            "task_id": task_id,
            "status": task.status
        }
    
    def add_task_log(self, task_id: str, step: str, message: str, level: str = "info") -> None:
        """
        添加任务日志
        """
        if task_id in self._tasks:
            self._tasks[task_id].logs.append(TaskLog(step=step, message=message, level=level))
    
    def get_task_logs(self, task_id: str) -> List[Dict[str, Any]]:
        """
        获取任务日志
        """
        if task_id not in self._tasks:
            return []
        
        return [log.to_dict() for log in self._tasks[task_id].logs]


class MockExecutorAdapter:
    """模拟任务执行器适配器"""
    
    def execute(self, task_id: str, task_spec: Dict[str, Any]) -> Dict[str, Any]:
        """模拟执行任务"""
        # 模拟执行逻辑
        task_type = task_spec.get("task_type")
        
        if task_type == "send_email":
            # 检查是否缺少必填参数
            params = task_spec.get("params", {})
            if "to" not in params:
                return {
                    "status": "awaiting_input",
                    "requiredField": "to",
                    "prompt": "请提供收件人邮箱地址"
                }
            elif "subject" not in params:
                return {
                    "status": "awaiting_input",
                    "requiredField": "subject",
                    "prompt": "请提供邮件主题"
                }
            else:
                # 模拟成功执行
                return {
                    "status": "completed",
                    "result": {
                        "message": f"邮件已发送到 {params['to']}",
                        "subject": params.get("subject"),
                        "to": params.get("to")
                    }
                }
        
        # 默认返回成功
        return {
            "status": "completed",
            "result": {
                "message": f"任务 {task_type} 执行成功"
            }
        }
    
    def cancel(self, task_id: str) -> None:
        """模拟取消任务"""
        pass
    
    def pause(self, task_id: str) -> None:
        """模拟暂停任务"""
        pass
    
    def resume(self, task_id: str, resume_input: Dict[str, Any]) -> Dict[str, Any]:
        """模拟恢复任务"""
        # 模拟恢复执行
        return {
            "status": "completed",
            "result": {
                "message": f"任务已恢复执行，使用输入: {resume_input}"
            }
        }
