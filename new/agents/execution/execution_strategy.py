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

class ParallelExecutionStrategy(ExecutionStrategy):
    """并行执行策略"""
    
    def __init__(self, max_concurrency: Optional[int] = None):
        """
        初始化并行执行策略
        
        Args:
            max_concurrency: 最大并发数，如果为None则无限制
        """
        super().__init__("parallel")
        self.max_concurrency = max_concurrency
    
    async def execute(self, tasks: List[Dict], 
                     executor_func: Callable[[Dict], Awaitable[Dict]]) -> Dict:
        """
        并行执行任务
        
        Args:
            tasks: 任务列表
            executor_func: 任务执行函数
            
        Returns:
            执行结果
        """
        logger.info(f"Starting parallel execution of {len(tasks)} tasks")
        
        if self.max_concurrency is not None:
            logger.info(f"With max concurrency: {self.max_concurrency}")
            # 使用信号量控制并发
            semaphore = asyncio.Semaphore(self.max_concurrency)
            
            async def execute_with_semaphore(task):
                async with semaphore:
                    try:
                        return await executor_func(task)
                    except Exception as e:
                        logger.error(f"Error in parallel task execution: {str(e)}")
                        return {
                            "success": False,
                            "error": str(e)
                        }
            
            # 并行执行所有任务
            coroutines = [execute_with_semaphore(task) for task in tasks]
            results = await asyncio.gather(*coroutines, return_exceptions=True)
            
        else:
            # 无限制并发
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
        
        logger.info(f"Parallel execution completed: {success}")
        
        return {
            "success": success,
            "results": processed_results,
            "strategy": "parallel",
            "tasks_executed": len(processed_results),
            "total_tasks": len(tasks),
            "max_concurrency": self.max_concurrency
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
        
        # Map阶段 - 并行执行所有任务
        parallel_strategy = ParallelExecutionStrategy()
        map_results = await parallel_strategy.execute(tasks, executor_func)
        
        # Reduce阶段 - 聚合结果
        logger.info("Starting reduce phase of Map-Reduce execution")
        aggregated_result = self.reduce_func(map_results["results"])
        
        logger.info(f"Map-Reduce execution completed")
        
        return {
            "success": map_results["success"],
            "raw_results": map_results["results"],
            "aggregated_result": aggregated_result,
            "strategy": "map_reduce",
            "map_success": map_results["success"],
            "tasks_executed": map_results["tasks_executed"],
            "total_tasks": len(tasks)
        }
    
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
        self.register_strategy(ParallelExecutionStrategy())
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
