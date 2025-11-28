"""Execution Actor - 任务执行处理者
负责处理智能体任务的执行逻辑，包括并行和顺序执行
与DataActor交互获取必要的执行参数
"""
from typing import Dict, Any, Optional
from thespian.actors import Actor
import logging

from capabilities import get_capability
from capabilities.connectors.connector_manager import UniversalConnectorManager
from capabilities.routing.context_resolver import ContextResolver
from .data_actor import DataActor
from common.messages import (
    TaskMessage,
    SubtaskResultMessage,
    SubtaskErrorMessage,
    DataQueryResponse,
    InvokeConnectorRequest,
    ConnectorExecutionSuccess,
    ConnectorExecutionFailure
)
from common.messages import DifySchemaResponse, DifyExecuteResponse

class ExecutionActor(Actor):
    """
    任务执行处理者
    - 处理叶子任务的执行
    - 与DataActor协作获取执行参数
    - 支持并行和顺序执行
    - 处理中间任务并生成子任务
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_actor = None
        self._pending_requests = {}
        self._pending_aggregators = {}
        # 初始化连接器管理器和上下文解析器
        self.connector_manager = UniversalConnectorManager()
        self.context_resolver = ContextResolver()
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化组件"""
        try:
            # 创建数据actor引用
            self.data_actor = self.createActor(DataActor)
            
            # Import here to avoid circular imports
            from capability_actors.result_aggregator_actor import ResultAggregatorActor
            self.ResultAggregatorActor = ResultAggregatorActor
            
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
            
            # 处理聚合完成消息
            elif isinstance(msg, dict) and msg.get("type") == "aggregation_complete":
                self._handle_aggregation_complete(msg, sender)
            
            # 处理聚合错误消息
            elif isinstance(msg, dict) and msg.get("type") == "aggregation_error":
                self._handle_aggregation_error(msg, sender)
            
            # 处理Dify Schema响应
            elif isinstance(msg, DifySchemaResponse):
                self._handle_dify_schema_response(msg)
            # 处理Dify执行响应
            elif isinstance(msg, DifyExecuteResponse):
                self._handle_dify_execute_response(msg)
            # 处理连接器执行成功响应
            elif isinstance(msg, ConnectorExecutionSuccess):
                self._handle_connector_execution_success(msg)
            # 处理连接器执行失败响应
            elif isinstance(msg, ConnectorExecutionFailure):
                self._handle_connector_execution_failure(msg)
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
        """处理来自DataActor的数据响应"""
        task_id = msg.task_id
        req_info = self._pending_requests.pop(task_id, None)
        
        if not req_info:
            self.logger.warning(f"No pending request found for task: {task_id}")
            return
        
        try:
            # 实际执行任务
            result = self._execute_task(task_id, msg.params, req_info)
            
            # 检查结果是否包含子任务
            if isinstance(result, dict) and "subtasks" in result:
                self._handle_subtasks_generation(task_id, result["subtasks"], req_info)
            else:
                # 没有子任务，直接返回结果
                self.send(req_info["sender"], {
                    "type": "subtask_result",
                    "task_id": task_id,
                    "result": result
                })
        except Exception as e:
            self.logger.error(f"Task execution failed: {task_id} - {str(e)}")
            self.send(req_info["sender"], SubtaskErrorMessage(task_id, str(e)))
    
    def _handle_subtasks_generation(self, task_id: str, subtasks: list, req_info: dict) -> None:
        """处理中间任务生成的子任务"""
        if not subtasks:
            # 没有子任务，返回空结果
            result_msg = SubtaskResultMessage(task_id, {})
            self.send(req_info["sender"], result_msg)
            return
        
        # 创建ResultAggregatorActor实例来处理子任务聚合
        aggregator = self.createActor(self.ResultAggregatorActor)
        
        # 初始化aggregator
        aggregator_init_msg = {
            "type": "initialize",
            "trace_id": task_id,
            "max_retries": 3,
            "timeout": 300,
            "aggregation_strategy": "map_reduce",
            "pending_tasks": [subtask["task_id"] for subtask in subtasks]
        }
        self.send(aggregator, aggregator_init_msg)
        
        # 保存聚合器信息
        self._pending_aggregators[task_id] = {
            "aggregator": aggregator,
            "sender": req_info["sender"],
            "task_id": task_id
        }
        
        # 发送每个子任务到执行队列
        for subtask in subtasks:
            self.send(self.data_actor, {
                "type": "get_capability_params",
                "capability": subtask["capability"],
                "task_id": subtask["task_id"]
            })
            
            # 记录子任务请求信息
            self._pending_requests[subtask["task_id"]] = {
                "context": subtask["context"],
                "memory": subtask["memory"],
                "capability": subtask["capability"],
                "sender": aggregator,  # 结果发送给aggregator
                "agent_id": subtask["agent_id"]
            }
    
    def _handle_aggregation_complete(self, msg: dict, sender: str) -> None:
        """处理聚合完成消息"""
        trace_id = msg.get("trace_id")
        if not trace_id:
            self.logger.warning("No trace_id found in aggregation complete message")
            return
        
        # 找到对应的任务信息
        pending_info = None
        for task_id, info in self._pending_aggregators.items():
            if info["aggregator"] == sender:
                pending_info = info
                del self._pending_aggregators[task_id]
                break
        
        if not pending_info:
            self.logger.warning(f"No pending aggregator found for sender: {sender}")
            return
        
        # 向原始发送者返回聚合结果
        result_msg = SubtaskResultMessage(pending_info["task_id"], msg["aggregated_result"])
        self.send(pending_info["sender"], result_msg)
    
    def _handle_aggregation_error(self, msg: dict, sender: str) -> None:
        """处理聚合错误消息"""
        trace_id = msg.get("trace_id")
        if not trace_id:
            self.logger.warning("No trace_id found in aggregation error message")
            return
        
        # 找到对应的任务信息
        pending_info = None
        for task_id, info in self._pending_aggregators.items():
            if info["aggregator"] == sender:
                pending_info = info
                del self._pending_aggregators[task_id]
                break
        
        if not pending_info:
            self.logger.warning(f"No pending aggregator found for sender: {sender}")
            return
        
        # 向原始发送者返回错误信息
        error_msg = SubtaskErrorMessage(pending_info["task_id"], msg["error"])
        self.send(pending_info["sender"], error_msg)
    
    def _execute_task(self, task_id: str, params: Dict[str, Any], req_info: Dict[str, Any]) -> None:
        """
        实际执行任务
        """
        capability = req_info["capability"]
        context = {**req_info["context"], **params.get("additional_context", {})}
        memory = req_info["memory"]
        
        try:
            result = None
            if capability == "dify_workflow":
                # 使用Connector Manager执行连接器操作
                result = self.connector_manager.execute(
                    connector_name="dify",
                    operation_name="execute",
                    inputs=context.get("inputs", {}),
                    params={
                        "api_key": context.get("api_key"),
                        "base_url": context.get("base_url"),
                        "user": context.get("user", "user")
                    }
                )
            else:
                # 本地能力执行
                # 使用新的能力获取方式
                try:
                    capability_instance = get_capability(capability, expected_type=Any)
                    if capability_instance:
                        result = capability_instance.execute(context=context, memory=memory)
                    else:
                        raise Exception(f"Capability not found: {capability}")
                except Exception as e:
                    # 兼容旧的执行方式
                    self.logger.warning(f"Failed to get capability using new method: {e}")
                    raise Exception(f"Capability execution failed: {str(e)}")
            
            # 发送任务结果
            result_msg = SubtaskResultMessage(task_id, result)
            self.send(req_info["sender"], result_msg)
            
        except Exception as e:
            error_msg = f"Task execution failed: {str(e)}"
            self.logger.error(error_msg)
            self.send(req_info["sender"], SubtaskErrorMessage(task_id, error_msg))
            
    def _handle_connector_execution_success(self, msg: ConnectorExecutionSuccess) -> None:
        """
        处理连接器执行成功响应
        """
        self.logger.info(f"Handling connector execution success for task: {msg.task_id}")
        result_msg = SubtaskResultMessage(msg.task_id, msg.result)
        self.send(msg.reply_to, result_msg)
    
    def _handle_connector_execution_failure(self, msg: ConnectorExecutionFailure) -> None:
        """
        处理连接器执行失败响应
        """
        self.logger.info(f"Handling connector execution failure for task: {msg.task_id}")
        error_msg = SubtaskErrorMessage(msg.task_id, msg.error)
        self.send(msg.reply_to, error_msg)