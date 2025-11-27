"""
任务执行服务
负责任务的实际执行、调度和资源管理
支持叶子节点任务和中间任务的执行
"""
import logging
import json
import queue
import time
from typing import Any, Dict, List, Optional, Callable
from thespian.actors import Actor
from capability_actors.execution_actor import ExecutionActor
from capability_actors.result_aggregator_actor import ResultAggregatorActor
from common.messages import SubtaskResultMessage, SubtaskErrorMessage

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskExecutionService(Actor):
    """任务执行服务"""
    
    def __init__(self):
        """初始化任务执行服务"""
        self._task_handlers: Dict[str, Callable] = {}
        self._capability_functions: Dict[str, Callable] = {}
        self._execution_queue = queue.Queue()
        self._max_concurrent_tasks = 10
        self._running_tasks: Dict[str, Any] = {}  # 存储当前运行的任务
        self._dify_client = None  # 将在运行时注入
        self._execution_actor = None  # ExecutionActor实例
        self._current_aggregator = None  # 当前聚合器实例
        self._group_sender = None  # 任务组发起者
        self._initialize_components()

    def _initialize_components(self):
        """初始化组件"""
        try:
            # 创建ExecutionActor实例
            self._execution_actor = self.createActor(ExecutionActor)
            logger.info("TaskExecutionService组件初始化成功")
        except Exception as e:
            logger.error(f"TaskExecutionService组件初始化失败: {str(e)}")
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """
        注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 任务处理函数
        """
        self._task_handlers[task_type] = handler
        logger.info(f"Registered task handler for type: {task_type}")
    
    def register_capability_function(self, capability_name: str, func: Callable):
        """
        注册能力函数
        
        Args:
            capability_name: 能力名称
            func: 能力函数
        """
        self._capability_functions[capability_name] = func
        logger.info(f"Registered capability function: {capability_name}")
    
    def execute_task(self, task_id: str, task_type: str, context: Dict,
                          capabilities: Optional[Dict] = None) -> Dict:
        """
        执行任务
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            context: 任务上下文
            capabilities: 可选的能力配置
            
        Returns:
            执行结果
        """
        try:
            logger.info(f"Starting execution of task {task_id} (type: {task_type})")
            
            # 根据任务类型选择处理器
            if task_type == "leaf_task":
                result = self._execute_leaf_task(task_id, context, capabilities)
            elif task_type == "intermediate_task":
                result = self._execute_intermediate_task(task_id, context, capabilities)
            elif task_type == "workflow_task":
                result = self._execute_workflow_task(task_id, context, capabilities)
            else:
                # 尝试使用注册的自定义处理器
                if task_type in self._task_handlers:
                    result = self._execute_with_custom_handler(task_id, task_type, context)
                else:
                    raise ValueError(f"No handler found for task type: {task_type}")
            
            logger.info(f"Task {task_id} completed successfully")
            return {
                "success": True,
                "result": result,
                "task_id": task_id
            }
            
        except Exception as e:
            logger.error(f"Error executing task {task_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "task_id": task_id
            }
    
    def _execute_leaf_task(self, task_id: str, context: Dict,
                                capabilities: Optional[Dict] = None) -> Dict:
        """
        执行叶子节点任务
        
        Args:
            task_id: 任务ID
            context: 任务上下文
            capabilities: 能力配置
            
        Returns:
            执行结果
        """
        # 检查是否需要调用能力函数
        if capabilities and "name" in capabilities:
            capability_name = capabilities["name"]
            
            if capability_name in self._capability_functions:
                # 调用注册的能力函数
                logger.info(f"Executing capability function: {capability_name} for task {task_id}")
                return self._capability_functions[capability_name](**(capabilities.get("params", {})))
            else:
                logger.warning(f"Capability function {capability_name} not found")
        
        # 默认处理逻辑
        return {
            "task_id": task_id,
            "status": "completed",
            "result_type": "leaf_result",
            "output": context.get("input_data", "Default output"),
            "metadata": {
                "execution_time": "now",
                "processed_by": "leaf_task_executor"
            }
        }
    
    def _execute_intermediate_task(self, task_id: str, context: Dict,
                                       capabilities: Optional[Dict] = None) -> Dict:
        """
        执行中间任务
        中间任务通常负责生成子任务或进行决策
        
        Args:
            task_id: 任务ID
            context: 任务上下文
            capabilities: 能力配置
            
        Returns:
            执行结果，可能包含子任务配置
        """
        # 提取任务目标和输入
        task_objective = context.get("objective", "")
        input_data = context.get("input_data", {})
        
        # 示例：根据输入数据生成子任务配置
        subtask_configs = []
        
        # 如果输入是列表，为每个项目创建子任务
        if isinstance(input_data, list):
            for item in input_data:
                subtask_configs.append({
                    "context": {
                        "input_data": item,
                        "objective": f"Process item: {item}"
                    },
                    "task_type": "leaf_task"
                })
        
        # 如果是字典，可能需要其他处理逻辑
        elif isinstance(input_data, dict):
            # 简单示例：根据字典中的键值对创建子任务
            for key, value in input_data.items():
                subtask_configs.append({
                    "context": {
                        "input_data": value,
                        "key": key,
                        "objective": f"Process key: {key}"
                    },
                    "task_type": "leaf_task"
                })
        
        result = {
            "task_id": task_id,
            "status": "processing",
            "result_type": "intermediate_result",
            "subtasks": subtask_configs,
            "subtasks_count": len(subtask_configs),
            "metadata": {
                "objective": task_objective,
                "execution_time": "now"
            }
        }
        
        logger.info(f"Intermediate task {task_id} generated {len(subtask_configs)} subtasks")
        return result
    
    def _execute_workflow_task(self, task_id: str, context: Dict,
                                   capabilities: Optional[Dict] = None) -> Dict:
        """
        执行工作流任务
        与Dify等工作流引擎交互
        
        Args:
            task_id: 任务ID
            context: 任务上下文
            capabilities: 能力配置
            
        Returns:
            执行结果
        """
        # 检查Dify客户端是否可用
        if not self._dify_client:
            raise ValueError("Dify client not initialized")
        
        try:
            # 提取工作流信息
            workflow_id = context.get("workflow_id")
            workflow_inputs = context.get("inputs", {})
            
            if not workflow_id:
                raise ValueError("Workflow ID is required")
            
            # 调用Dify工作流执行
            logger.info(f"Executing Dify workflow {workflow_id} for task {task_id}")
            
            # 这里是与Dify交互的逻辑，需要根据实际API进行调整
            # 示例代码：
            response = self._dify_client.execute_workflow(
                workflow_id=workflow_id,
                inputs=workflow_inputs,
                user="system"
            )
            
            # 处理Dify响应
            if isinstance(response, dict):
                result = {
                    "task_id": task_id,
                    "status": "completed",
                    "result_type": "workflow_result",
                    "output": response.get("output", {}),
                    "workflow_id": workflow_id,
                    "execution_id": response.get("execution_id", "unknown"),
                    "metadata": {
                        "executed_by": "dify_workflow",
                        "execution_time": "now"
                    }
                }
                
                # 检查是否需要生成子任务
                if "subtasks" in response:
                    result["subtasks"] = response["subtasks"]
                    result["status"] = "processing"
                    
                return result
            
            return {
                "task_id": task_id,
                "status": "completed",
                "result_type": "workflow_result",
                "output": str(response),
                "workflow_id": workflow_id,
                "metadata": {
                    "executed_by": "dify_workflow",
                    "execution_time": "now"
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing workflow task {task_id}: {str(e)}")
            raise
    
    
    def _execute_with_custom_handler(self, task_id: str, task_type: str,
                                         context: Dict) -> Dict:
        """
        使用自定义处理器执行任务
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            context: 任务上下文
            
        Returns:
            执行结果
        """
        handler = self._task_handlers[task_type]
        
        # 直接调用处理器（所有处理器都应该是同步的）
        result = handler(task_id, context)
        
        return result
    
   
    
    def set_dify_client(self, dify_client):
        """
        设置Dify客户端
        
        Args:
            dify_client: Dify客户端实例
        """
        self._dify_client = dify_client
        logger.info("Dify client set")

    def receiveMessage(self, msg: Any, sender: Any) -> None:
        """处理接收到的消息"""
        try:
            if isinstance(msg, dict):
                msg_type = msg.get("type")
                if msg_type == "execute_task_group":
                    self._handle_execute_task_group(msg, sender)
                elif msg_type == "register_task_handler":
                    self._handle_register_task_handler(msg)
                elif msg_type == "register_capability_function":
                    self._handle_register_capability_function(msg)
                elif msg_type == "set_dify_client":
                    self._handle_set_dify_client(msg)
                elif msg_type == "execute_task":
                    self._handle_execute_task(msg, sender)
                elif msg_type == "aggregation_complete":
                    self._handle_aggregation_complete(msg, sender)
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
            elif isinstance(msg, SubtaskResultMessage):
                # 处理子任务成功结果
                self._handle_subtask_result(msg.__dict__, sender)
            elif isinstance(msg, SubtaskErrorMessage):
                # 处理子任务失败错误
                self._handle_subtask_error(msg.__dict__, sender)
            else:
                logger.warning(f"Unknown message type: {type(msg)}")
        except Exception as e:
            logger.error(f"TaskExecutionService error handling message: {str(e)}")
            # 发送错误消息回发送者
            if isinstance(msg, dict) and "task_id" in msg:
                self.send(sender, SubtaskErrorMessage(msg["task_id"], str(e)))
            elif hasattr(msg, "task_id"):
                self.send(sender, SubtaskErrorMessage(getattr(msg, "task_id"), str(e)))

    def _handle_execute_task_group(self, msg: Dict, sender: Any) -> None:
        """处理任务组执行请求"""
        tasks = msg.get("tasks", [])
        if not tasks:
            self.send(sender, {
                "type": "task_group_result",
                "success": True,
                "result": [],
                "task_ids": []
            })
            return

        # 创建ResultAggregatorActor实例
        aggregator = self.createActor(ResultAggregatorActor)

        # 初始化aggregator
        aggregator_init_msg = {
            "type": "initialize",
            "trace_id": msg.get("trace_id", ""),
            "max_retries": msg.get("max_retries", 3),
            "timeout": msg.get("timeout", 300),
            "aggregation_strategy": msg.get("aggregation_strategy", "map_reduce"),
            "pending_tasks": [task["task_id"] for task in tasks]
        }
        self.send(aggregator, aggregator_init_msg)

        # 保存当前聚合器和发送者信息
        self._current_aggregator = aggregator
        self._group_sender = sender

        # 发送每个任务到ExecutionActor执行
        for task in tasks:
            task_msg = {
                "type": "leaf_task",
                "task_id": task["task_id"],
                "context": task["context"],
                "memory": task["memory"],
                "capability": task["capability"],
                "agent_id": task["agent_id"]
            }
            self.send(self._execution_actor, task_msg)

    def _handle_register_task_handler(self, msg: Dict) -> None:
        """处理注册任务处理器消息"""
        task_type = msg.get("task_type")
        handler = msg.get("handler")
        if task_type and handler:
            self.register_task_handler(task_type, handler)

    def _handle_register_capability_function(self, msg: Dict) -> None:
        """处理注册能力函数消息"""
        capability_name = msg.get("capability_name")
        func = msg.get("func")
        if capability_name and func:
            self.register_capability_function(capability_name, func)

    def _handle_set_dify_client(self, msg: Dict) -> None:
        """处理设置Dify客户端消息"""
        dify_client = msg.get("dify_client")
        if dify_client:
            self.set_dify_client(dify_client)

    def _handle_execute_task(self, msg: Dict, sender: Any) -> None:
        """处理单任务执行请求"""
        task_id = msg.get("task_id")
        task_type = msg.get("task_type")
        context = msg.get("context", {})
        capabilities = msg.get("capabilities")

        if not task_id or not task_type:
            self.send(sender, SubtaskErrorMessage("unknown", "Missing task_id or task_type"))
            return

        try:
            result = self.execute_task(task_id, task_type, context, capabilities)
            self.send(sender, SubtaskResultMessage(task_id, result))
        except Exception as e:
            self.send(sender, SubtaskErrorMessage(task_id, str(e)))

    def _handle_subtask_result(self, result_msg: Dict, sender: Any) -> None:
        """处理子任务成功结果"""
        if hasattr(self, "_current_aggregator") and self._current_aggregator:
            self.send(self._current_aggregator, {
                "type": "subtask_result",
                "task_id": result_msg["task_id"],
                "result": result_msg["result"]
            })

    def _handle_subtask_error(self, error_msg: Dict, sender: Any) -> None:
        """处理子任务失败错误"""
        if hasattr(self, "_current_aggregator") and self._current_aggregator:
            self.send(self._current_aggregator, {
                "type": "subtask_error",
                "task_id": error_msg["task_id"],
                "error": error_msg["error"]
            })

    def _handle_aggregation_complete(self, msg: Dict, sender: Any) -> None:
        """处理聚合完成消息"""
        logger.info(f"Received aggregation complete message: {msg.get('trace_id')}")
        if self._group_sender:
            # 构造任务组结果并返回给发起者
            task_group_result = {
                "type": "task_group_result",
                "success": msg["success"],
                "aggregated_result": msg["aggregated_result"],
                "completed_tasks": msg["completed_tasks"],
                "failed_tasks": msg["failed_tasks"],
                "total_tasks": msg["total_tasks"],
                "strategy": msg["strategy"],
                "trace_id": msg["trace_id"]
            }
            self.send(self._group_sender, task_group_result)
        # 清理资源
        self._group_sender = None
        self._current_aggregator = None
    
    def schedule_task(self, task_id: str, task_type: str, context: Dict):
        """
        调度任务到执行队列
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            context: 任务上下文
        """
        self._execution_queue.put({
            "task_id": task_id,
            "task_type": task_type,
            "context": context
        })
    
    def start_execution_loop(self):
        """
        启动任务执行循环
        """
        logger.info("Starting task execution loop")
        
        while True:
            try:
                # 等待新任务
                task_data = self._execution_queue.get(block=True)
                
                # 执行任务（同步执行）
                try:
                    self.execute_task(
                        task_id=task_data["task_id"],
                        task_type=task_data["task_type"],
                        context=task_data["context"]
                    )
                except Exception as e:
                    logger.error(f"Error executing task {task_data['task_id']} in loop: {str(e)}")
                
                # 标记队列任务为完成
                self._execution_queue.task_done()
                
            except Exception as e:
                logger.error(f"Error in execution loop: {str(e)}")
    
    def stop_execution_loop(self):
        """
        停止任务执行循环
        """
        logger.info("Stopping task execution loop")
        
        # 清理运行中的任务（同步模型下任务会立即完成，因此这里只需要清空列表）
        self._running_tasks.clear()
    
    def get_execution_status(self) -> Dict:
        """
        获取执行状态信息
        
        Returns:
            执行状态信息
        """
        return {
            "queue_size": self._execution_queue.qsize(),
            "running_tasks": len(self._running_tasks),
            "max_concurrent_tasks": self._max_concurrent_tasks,
            "registered_task_types": list(self._task_handlers.keys()),
            "registered_capabilities": list(self._capability_functions.keys())
        }
