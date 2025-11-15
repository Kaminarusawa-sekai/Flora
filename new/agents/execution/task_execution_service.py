"""
任务执行服务
负责任务的实际执行、调度和资源管理
支持叶子节点任务和中间任务的执行
"""
import asyncio
import logging
import json
from typing import Any, Dict, List, Optional, Callable, Awaitable

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskExecutionService:
    """任务执行服务"""
    
    def __init__(self):
        """初始化任务执行服务"""
        self._task_handlers: Dict[str, Callable] = {}
        self._capability_functions: Dict[str, Callable] = {}
        self._execution_queue = asyncio.Queue()
        self._max_concurrent_tasks = 10
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._dify_client = None  # 将在运行时注入
    
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
    
    async def execute_task(self, task_id: str, task_type: str, context: Dict,
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
                result = await self._execute_leaf_task(task_id, context, capabilities)
            elif task_type == "intermediate_task":
                result = await self._execute_intermediate_task(task_id, context, capabilities)
            elif task_type == "workflow_task":
                result = await self._execute_workflow_task(task_id, context, capabilities)
            elif task_type == "data_query_task":
                result = await self._execute_data_query_task(task_id, context)
            else:
                # 尝试使用注册的自定义处理器
                if task_type in self._task_handlers:
                    result = await self._execute_with_custom_handler(task_id, task_type, context)
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
    
    async def _execute_leaf_task(self, task_id: str, context: Dict,
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
                return await self._capability_functions[capability_name](**(capabilities.get("params", {})))
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
    
    async def _execute_intermediate_task(self, task_id: str, context: Dict,
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
    
    async def _execute_workflow_task(self, task_id: str, context: Dict,
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
            response = await self._dify_client.execute_workflow(
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
    
    async def _execute_data_query_task(self, task_id: str, context: Dict) -> Dict:
        """
        执行数据查询任务
        
        Args:
            task_id: 任务ID
            context: 任务上下文，包含查询信息
            
        Returns:
            查询结果
        """
        # 提取查询参数
        query_type = context.get("query_type")
        query_params = context.get("params", {})
        
        # 根据查询类型执行不同的查询逻辑
        if query_type == "db_query":
            result = await self._execute_db_query(query_params)
        elif query_type == "api_call":
            result = await self._execute_api_call(query_params)
        elif query_type == "file_search":
            result = await self._execute_file_search(query_params)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
        
        return {
            "task_id": task_id,
            "status": "completed",
            "result_type": "data_query_result",
            "data": result,
            "query_type": query_type,
            "metadata": {
                "execution_time": "now"
            }
        }
    
    async def _execute_with_custom_handler(self, task_id: str, task_type: str,
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
        
        # 检查处理器是否为协程函数
        if asyncio.iscoroutinefunction(handler):
            result = await handler(task_id, context)
        else:
            # 如果不是协程函数，在默认执行器中运行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, handler, task_id, context)
        
        return result
    
    async def _execute_db_query(self, params: Dict) -> Any:
        """
        执行数据库查询
        
        Args:
            params: 查询参数
            
        Returns:
            查询结果
        """
        # 这是示例实现，实际应该连接到数据库并执行查询
        db_type = params.get("db_type", "generic")
        query = params.get("query", "")
        
        logger.info(f"Executing DB query: {query} (type: {db_type})")
        
        # 模拟查询结果
        return {
            "query": query,
            "results": [
                {"id": 1, "name": "Example Item 1"},
                {"id": 2, "name": "Example Item 2"}
            ],
            "count": 2,
            "db_type": db_type
        }
    
    async def _execute_api_call(self, params: Dict) -> Any:
        """
        执行API调用
        
        Args:
            params: API调用参数
            
        Returns:
            API响应
        """
        url = params.get("url", "")
        method = params.get("method", "GET")
        headers = params.get("headers", {})
        body = params.get("body")
        
        logger.info(f"Executing API call: {method} {url}")
        
        # 模拟API调用
        # 实际实现应该使用aiohttp或其他异步HTTP客户端
        return {
            "url": url,
            "method": method,
            "status": 200,
            "data": {
                "message": "Success",
                "timestamp": "now"
            },
            "headers": headers
        }
    
    async def _execute_file_search(self, params: Dict) -> Any:
        """
        执行文件搜索
        
        Args:
            params: 搜索参数
            
        Returns:
            搜索结果
        """
        query = params.get("query", "")
        file_pattern = params.get("file_pattern", "*")
        search_path = params.get("path", ".")
        
        logger.info(f"Executing file search: '{query}' in {search_path} (pattern: {file_pattern})")
        
        # 模拟文件搜索结果
        return {
            "query": query,
            "files": [
                {"path": f"{search_path}/file1.txt", "score": 0.95},
                {"path": f"{search_path}/file2.txt", "score": 0.85}
            ],
            "total_matches": 2
        }
    
    def set_dify_client(self, dify_client):
        """
        设置Dify客户端
        
        Args:
            dify_client: Dify客户端实例
        """
        self._dify_client = dify_client
        logger.info("Dify client set")
    
    async def schedule_task(self, task_id: str, task_type: str, context: Dict):
        """
        调度任务到执行队列
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            context: 任务上下文
        """
        await self._execution_queue.put({
            "task_id": task_id,
            "task_type": task_type,
            "context": context
        })
    
    async def start_execution_loop(self):
        """
        启动任务执行循环
        """
        logger.info("Starting task execution loop")
        
        while True:
            try:
                # 等待新任务
                task_data = await self._execution_queue.get()
                
                # 检查并发任务限制
                if len(self._running_tasks) >= self._max_concurrent_tasks:
                    logger.warning("Maximum concurrent tasks reached, waiting...")
                    # 等待至少一个任务完成
                    while len(self._running_tasks) >= self._max_concurrent_tasks:
                        await asyncio.sleep(0.1)
                
                # 执行任务
                task = asyncio.create_task(self.execute_task(
                    task_id=task_data["task_id"],
                    task_type=task_data["task_type"],
                    context=task_data["context"]
                ))
                
                # 保存任务引用
                self._running_tasks[task_data["task_id"]] = task
                
                # 设置完成回调
                task.add_done_callback(
                    lambda t, task_id=task_data["task_id"]: 
                    self._running_tasks.pop(task_id, None)
                )
                
                # 标记队列任务为完成
                self._execution_queue.task_done()
                
            except asyncio.CancelledError:
                logger.info("Task execution loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in execution loop: {str(e)}")
    
    async def stop_execution_loop(self):
        """
        停止任务执行循环
        """
        logger.info("Stopping task execution loop")
        
        # 取消所有运行中的任务
        for task_id, task in list(self._running_tasks.items()):
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    logger.info(f"Cancelled task {task_id}")
        
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
