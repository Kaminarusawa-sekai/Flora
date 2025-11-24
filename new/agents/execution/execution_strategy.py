"""
执行策略服务
负责管理和应用不同的任务执行策略
支持顺序执行、并行执行、条件执行等多种策略
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional, Callable, Awaitable

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExecutionStrategy:
    """执行策略基类"""
    
    def __init__(self, strategy_name: str):
        """
        初始化执行策略
        
        Args:
            strategy_name: 策略名称
        """
        self.strategy_name = strategy_name
        logger.info(f"Initialized execution strategy: {strategy_name}")
    
    async def execute(self, tasks: List[Dict], 
                     executor_func: Callable[[Dict], Awaitable[Dict]]) -> Dict:
        """
        执行策略
        
        Args:
            tasks: 任务列表
            executor_func: 任务执行函数
            
        Returns:
            执行结果
        """
        raise NotImplementedError("Subclasses must implement execute method")
    
    def get_strategy_info(self) -> Dict:
        """
        获取策略信息
        
        Returns:
            策略信息字典
        """
        return {
            "name": self.strategy_name
        }

class SequentialExecutionStrategy(ExecutionStrategy):
    """顺序执行策略"""
    
    def __init__(self):
        """初始化顺序执行策略"""
        super().__init__("sequential")
    
    async def execute(self, tasks: List[Dict], 
                     executor_func: Callable[[Dict], Awaitable[Dict]]) -> Dict:
        """
        按顺序执行任务
        
        Args:
            tasks: 任务列表
            executor_func: 任务执行函数
            
        Returns:
            执行结果
        """
        results = []
        success = True
        
        logger.info(f"Starting sequential execution of {len(tasks)} tasks")
        
        for i, task in enumerate(tasks):
            try:
                logger.info(f"Executing task {i+1}/{len(tasks)} in sequential mode")
                result = await executor_func(task)
                results.append(result)
                
                # 如果任务失败，根据配置决定是否继续
                if not result.get("success", False):
                    success = False
                    logger.warning(f"Task {i+1} failed, continuing execution")
                    
            except Exception as e:
                logger.error(f"Error executing task {i+1}: {str(e)}")
                success = False
                results.append({
                    "success": False,
                    "error": str(e),
                    "task_index": i
                })
        
        logger.info(f"Sequential execution completed: {success}")
        
        return {
            "success": success,
            "results": results,
            "strategy": "sequential",
            "tasks_executed": len(results),
            "total_tasks": len(tasks)
        }



class ConditionalExecutionStrategy(ExecutionStrategy):
    """条件执行策略"""
    
    def __init__(self):
        """初始化条件执行策略"""
        super().__init__("conditional")
    
    async def execute(self, tasks: List[Dict], 
                     executor_func: Callable[[Dict], Awaitable[Dict]]) -> Dict:
        """
        条件执行任务
        根据前一个任务的结果决定是否执行下一个任务
        
        Args:
            tasks: 任务列表，每个任务可以包含条件配置
            executor_func: 任务执行函数
            
        Returns:
            执行结果
        """
        results = []
        success = True
        should_continue = True
        
        logger.info(f"Starting conditional execution of {len(tasks)} tasks")
        
        for i, task in enumerate(tasks):
            if not should_continue:
                logger.info(f"Skipping task {i+1} due to condition not met")
                results.append({
                    "success": None,
                    "skipped": True,
                    "reason": "previous_condition_failed",
                    "task_index": i
                })
                continue
            
            try:
                logger.info(f"Executing task {i+1}/{len(tasks)} in conditional mode")
                result = await executor_func(task)
                results.append(result)
                
                # 检查是否需要继续执行
                condition_type = task.get("conditions", {}).get("type", "always")
                
                if condition_type == "on_success" and not result.get("success", False):
                    should_continue = False
                    logger.info(f"Task {i+1} failed, stopping conditional execution")
                    success = False
                elif condition_type == "on_failure" and result.get("success", False):
                    should_continue = False
                    logger.info(f"Task {i+1} succeeded, stopping conditional execution")
                
            except Exception as e:
                logger.error(f"Error executing task {i+1}: {str(e)}")
                success = False
                should_continue = False
                results.append({
                    "success": False,
                    "error": str(e),
                    "task_index": i
                })
        
        logger.info(f"Conditional execution completed: {success}")
        
        return {
            "success": success,
            "results": results,
            "strategy": "conditional",
            "tasks_executed": len([r for r in results if not r.get("skipped", False)]),
            "total_tasks": len(tasks)
        }

class MapReduceExecutionStrategy(ExecutionStrategy):
    """Map-Reduce执行策略"""
    
    def __init__(self, reduce_func: Optional[Callable] = None):
        """
        初始化Map-Reduce执行策略
        
        Args:
            reduce_func: 归约函数，用于聚合结果
        """
        super().__init__("map_reduce")
        self.reduce_func = reduce_func or self._default_reduce
    
    async def execute(self, tasks: List[Dict], 
                     executor_func: Callable[[Dict], Awaitable[Dict]]) -> Dict:
        """
        执行Map-Reduce策略
        1. Map阶段：并行执行所有任务
        2. Reduce阶段：聚合所有结果
        
        Args:
            tasks: 任务列表
            executor_func: 任务执行函数
            
        Returns:
            执行结果，包含聚合后的结果
        """
        logger.info(f"Starting Map-Reduce execution with {len(tasks)} tasks")
        
        # 对于Thespian场景，我们需要确保生成唯一的trace_id来跟踪整个执行流程
        from new.capability_actors.result_aggregator_actor import ResultAggregatorActor
        from thespian.actors import ActorSystem
        
        # 创建Actor系统并初始化ResultAggregatorActor
        actor_system = ActorSystem()
        
        try:
            # 生成唯一的trace_id用于跟踪
            import uuid
            trace_id = str(uuid.uuid4())
            logger.info(f"Generated trace_id for Map-Reduce execution: {trace_id}")
            
            # 创建ResultAggregatorActor
            aggregator = actor_system.createActor(ResultAggregatorActor)

            # 生成所有任务ID并添加到任务中
            tasks_with_ids = []
            for i, task in enumerate(tasks):
                task_id = task.get("task_id", f"task_{i}")
                tasks_with_ids.append({**task, "task_id": task_id})
            
            # 创建任务ID到任务的映射
            task_id_to_task = {task["task_id"]: task for task in tasks_with_ids}
            task_ids = list(task_id_to_task.keys())
            
            # 初始化聚合器
            actor_system.tell(aggregator, {
                "type": "initialize",
                "pending_tasks": task_ids,
                "trace_id": trace_id,
                "max_retries": 3,
                "aggregation_strategy": "map_reduce",
                "reduce_func": self.reduce_func
            })
            
            # 直接使用asyncio.gather并行执行所有任务
            coroutines = [executor_func(task) for task in tasks]
            results = await asyncio.gather(*coroutines, return_exceptions=True)
            
            # 处理异常结果
            processed_results = []
            success = True
            
            for result in results:
                if isinstance(result, Exception):
                    processed_results.append({
                        "success": False,
                        "error": str(result)
                    })
                    success = False
                else:
                    processed_results.append(result)
                    if not result.get("success", False):
                        success = False
            
            # 创建任务ID到原始任务的映射，用于处理重试
            task_id_to_task = {}
            for i, task in enumerate(tasks):
                task_id = task.get("task_id", f"task_{i}")
                task_id_to_task[task_id] = task
            
            # 将结果传递给聚合器进行处理
            for i, result in enumerate(processed_results):
                task_id = result.get("task_id", f"task_{i}")
                if result.get("success", False):
                    actor_system.tell(aggregator, {
                        "type": "subtask_result",
                        "task_id": task_id,
                        "result": result,
                        "trace_id": trace_id
                    })
                else:
                    error_msg = result.get("error", "Unknown error")
                    actor_system.tell(aggregator, {
                        "type": "subtask_error",
                        "task_id": task_id,
                        "error": error_msg,
                        "trace_id": trace_id
                    })
            
            # 从聚合器获取最终结果，处理重试
            final_result = None
            while True:
                final_result = actor_system.ask(aggregator, {
                    "type": "get_final_result",
                    "trace_id": trace_id
                }, timeout=60)
                
                if final_result["type"] == "aggregation_complete":
                    break
                elif final_result["type"] == "retry_subtask":
                    # 处理重试请求
                    task_id = final_result["task_id"]
                    if task_id not in task_id_to_task:
                        logger.error(f"Task {task_id} not found in task map")
                        break
                    
                    # 执行重试
                    original_task = task_id_to_task[task_id]
                    retry_result = await executor_func(original_task)
                    
                    # 将重试结果发送回聚合器
                    if retry_result.get("success", False):
                        actor_system.tell(aggregator, {
                            "type": "subtask_result",
                            "task_id": task_id,
                            "result": retry_result,
                            "trace_id": trace_id
                        })
                    else:
                        error_msg = retry_result.get("error", "Unknown error")
                        actor_system.tell(aggregator, {
                            "type": "subtask_error",
                            "task_id": task_id,
                            "error": error_msg,
                            "trace_id": trace_id
                        })
                elif final_result["type"] == "aggregation_in_progress":
                    # 继续等待聚合完成
                    continue
                else:
                    # 未知消息类型
                    logger.error(f"Unexpected message type from aggregator: {final_result['type']}")
                    break
            
            logger.info(f"Map-Reduce execution completed with trace_id: {trace_id}")
            
            # 转换结果格式以保持向后兼容
            return {
                "success": final_result.get("success", False),
                "raw_results": map_results["results"],
                "aggregated_result": final_result.get("aggregated_result", {}),
                "strategy": "map_reduce",
                "map_success": map_results["success"],
                "tasks_executed": map_results["tasks_executed"],
                "total_tasks": len(tasks),
                "trace_id": trace_id,
                "completed_tasks": final_result.get("completed_tasks", {}),
                "failed_tasks": final_result.get("failed_tasks", {})
            }
        except Exception as e:
            logger.error(f"Map-Reduce execution failed: {e}")
            # 回退到原来的执行方式，确保向下兼容
            logger.info("Falling back to original Map-Reduce execution")
            
            # Map阶段 - 并行执行所有任务
            parallel_strategy = ParallelExecutionStrategy()
            map_results = await parallel_strategy.execute(tasks, executor_func)
            
            # Reduce阶段 - 聚合结果
            logger.info("Starting reduce phase of Map-Reduce execution (fallback)")
            aggregated_result = self.reduce_func(map_results["results"])
            
            logger.info(f"Map-Reduce execution completed (fallback)")
            
            return {
                "success": map_results["success"],
                "raw_results": map_results["results"],
                "aggregated_result": aggregated_result,
                "strategy": "map_reduce",
                "map_success": map_results["success"],
                "tasks_executed": map_results["tasks_executed"],
                "total_tasks": len(tasks),
                "error": str(e)  # 记录降级原因
            }
        finally:
            # 关闭Actor系统
            actor_system.shutdown()
    
    def _default_reduce(self, results: List[Dict]) -> Dict:
        """
        默认的归约函数
        简单聚合结果
        
        Args:
            results: 任务执行结果列表
            
        Returns:
            聚合后的结果
        """
        success_count = sum(1 for r in results if r.get("success", False))
        failure_count = sum(1 for r in results if not r.get("success", True))
        
        # 聚合成功结果中的数据
        aggregated_data = []
        for result in results:
            if result.get("success", False) and "result" in result:
                aggregated_data.append(result["result"])
        
        return {
            "success_rate": success_count / len(results) if results else 0,
            "success_count": success_count,
            "failure_count": failure_count,
            "aggregated_data": aggregated_data,
            "total_results": len(results)
        }

class ExecutionStrategyManager:
    """执行策略管理器"""
    
    def __init__(self):
        """初始化策略管理器"""
        self.strategies: Dict[str, ExecutionStrategy] = {}
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """注册默认策略"""
        self.register_strategy(SequentialExecutionStrategy())
        self.register_strategy(ConditionalExecutionStrategy())
        self.register_strategy(MapReduceExecutionStrategy())
    
    def register_strategy(self, strategy: ExecutionStrategy):
        """
        注册执行策略
        
        Args:
            strategy: 执行策略实例
        """
        self.strategies[strategy.strategy_name] = strategy
        logger.info(f"Registered execution strategy: {strategy.strategy_name}")
    
    def get_strategy(self, strategy_name: str) -> Optional[ExecutionStrategy]:
        """
        获取指定策略
        
        Args:
            strategy_name: 策略名称
            
        Returns:
            执行策略实例，如果不存在则返回None
        """
        if strategy_name not in self.strategies:
            logger.warning(f"Strategy '{strategy_name}' not found")
            return None
        
        return self.strategies[strategy_name]
    
    async def execute_with_strategy(self, strategy_name: str, tasks: List[Dict],
                                   executor_func: Callable[[Dict], Awaitable[Dict]]) -> Dict:
        """
        使用指定策略执行任务
        
        Args:
            strategy_name: 策略名称
            tasks: 任务列表
            executor_func: 任务执行函数
            
        Returns:
            执行结果
        """
        strategy = self.get_strategy(strategy_name)
        
        if not strategy:
            raise ValueError(f"Unknown execution strategy: {strategy_name}")
        
        return await strategy.execute(tasks, executor_func)
    
    def list_strategies(self) -> List[Dict]:
        """
        列出所有可用策略
        
        Returns:
            策略信息列表
        """
        return [strategy.get_strategy_info() for strategy in self.strategies.values()]
    
    def create_custom_strategy(self, strategy_name: str, 
                             execute_func: Callable[[List[Dict], Callable], Awaitable[Dict]]) -> ExecutionStrategy:
        """
        创建自定义策略
        
        Args:
            strategy_name: 策略名称
            execute_func: 执行函数
            
        Returns:
            自定义执行策略
        """
        # 创建动态子类
        CustomStrategy = type(
            f"Custom{strategy_name.capitalize()}Strategy",
            (ExecutionStrategy,),
            {
                "__init__": lambda self: super(CustomStrategy, self).__init__(strategy_name),
                "execute": execute_func
            }
        )
        
        strategy = CustomStrategy()
        self.register_strategy(strategy)
        
        return strategy

# 创建全局策略管理器实例
global_strategy_manager = ExecutionStrategyManager()

def get_strategy_manager() -> ExecutionStrategyManager:
    """
    获取全局策略管理器
    
    Returns:
        策略管理器实例
    """
    return global_strategy_manager
