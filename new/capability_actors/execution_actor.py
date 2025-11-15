"""Execution Actor - 任务执行处理者
负责处理智能体任务的执行逻辑，包括并行和顺序执行
与DataActor交互获取必要的执行参数
"""
from typing import Dict, Any, Optional
from thespian.actors import Actor
import logging

from new.agents.parallel.execution_manager import ParallelExecutionManager
from new.capability_actors.data_actor import DataActor
from new.common.messages import (
    TaskMessage,
    SubtaskResultMessage,
    SubtaskErrorMessage,
    DataQueryResponse
)

class ExecutionActor(Actor):
    """
    任务执行处理者
    - 处理叶子任务的执行
    - 与DataActor协作获取执行参数
    - 支持并行和顺序执行
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_actor = None
        self.parallel_execution_manager = None
        self._pending_requests = {}  # 存储等待数据响应的请求
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化组件"""
        try:
            # 创建数据actor引用
            self.data_actor = self.createActor(DataActor)
            
            # 初始化并行执行管理器
            from new.agents.parallel.execution_manager import ParallelExecutionManager
            self.parallel_execution_manager = ParallelExecutionManager()
            
            self.logger.info("ExecutionActor组件初始化成功")
        except Exception as e:
            self.logger.error(f"ExecutionActor组件初始化失败: {e}")
    
    def receiveMessage(self, msg: Any, sender: str) -> None:
        """
        接收消息并处理
        
        Args:
            msg: 消息内容
            sender: 发送者
        """
        try:
            # 处理叶子任务请求
            if isinstance(msg, dict) and msg.get("type") == "leaf_task":
                self._handle_leaf_task_request(msg, sender)
            
            # 处理数据查询响应（来自DataActor）
            elif isinstance(msg, DataQueryResponse):
                self._handle_data_response(msg)
            
            # 处理其他任务类型
            else:
                self.logger.warning(f"Unknown message type: {type(msg)}")
                task_id = msg.get("task_id", "unknown") if isinstance(msg, dict) else getattr(msg, "task_id", "unknown")
                self.send(sender, SubtaskErrorMessage(task_id, f"Unknown message type: {type(msg)}"))
        except Exception as e:
            self.logger.error(f"Execution failed: {e}")
            task_id = getattr(msg, "task_id", "unknown")
            self.send(sender, SubtaskErrorMessage(task_id, str(e)))
    
    def _handle_leaf_task_request(self, msg: Dict[str, Any], sender: str) -> None:
        """处理叶子任务请求"""
        self.logger.info(f"Handling leaf task: {msg['task_id']}")
        
        # 记录等待的数据请求
        self._pending_requests[msg['task_id']] = {
            "context": msg['context'],
            "memory": msg['memory'],
            "capability": msg['capability'],
            "sender": sender,
            "agent_id": msg['agent_id']
        }
        
        # 向DataActor请求获取执行参数
        self.send(self.data_actor, {
            "type": "get_capability_params",
            "capability": msg['capability'],
            "task_id": msg['task_id']
        })
    
    def _handle_data_response(self, msg: DataQueryResponse) -> None:
        """处理来自DataActor的参数响应"""
        task_id = msg.request_id
        
        if task_id not in self._pending_requests:
            self.logger.warning(f"Orphaned data response for task: {task_id}")
            return
        
        # 获取请求上下文
        req_info = self._pending_requests.pop(task_id)
        
        # 执行任务
        try:
            if msg.error:
                raise Exception(msg.error)
            
            params = msg.result
            self.logger.info(f"Executing task {task_id} with params: {params}")
            
            # 根据能力类型执行任务
            result = self._execute_task(task_id, params, req_info)
            
            # 返回结果给原发送者
            self.send(req_info["sender"], SubtaskResultMessage(task_id, result))
            self.logger.info(f"Task {task_id} executed successfully")
        except Exception as e:
            self.logger.error(f"Task execution failed: {e}")
            self.send(req_info["sender"], SubtaskErrorMessage(task_id, str(e)))
    
    def _execute_task(self, task_id: str, params: Dict[str, Any], req_info: Dict[str, Any]) -> Any:
        """实际执行任务"""
        capability = req_info["capability"]
        context = {**req_info["context"], **params.get("additional_context", {})}
        memory = req_info["memory"]
        
        if capability != "dify_workflow":
            # 执行普通能力函数
            return self.parallel_execution_manager.execute_capability(
                capability=capability,
                context=context,
                memory=memory
            )
        
        # 执行dify工作流
        return self.parallel_execution_manager.execute_workflow(
            task_id=task_id,
            context=context,
            memory=memory,
            sender=req_info["sender"],
            api_key=params.get("api_key"),
            base_url=params.get("base_url", "DIFY_URI")  # 默认值
        )