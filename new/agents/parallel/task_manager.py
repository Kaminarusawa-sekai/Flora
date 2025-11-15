"""
并行任务管理器
负责管理和协调并行任务的执行
提供任务分发、状态跟踪、结果收集等功能
"""
import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional, Callable, Awaitable, Set
from dataclasses import dataclass, field

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class TaskInfo:
    """任务信息数据类"""
    task_id: str
    task_data: Dict
    status: str = "pending"
    result: Optional[Dict] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    dependencies: Set[str] = field(default_factory=set)

class ParallelTaskManager:
    """并行任务管理器"""
    
    def __init__(self, max_concurrency: Optional[int] = None):
        """
        初始化并行任务管理器
        
        Args:
            max_concurrency: 最大并发数，如果为None则无限制
        """
        self.max_concurrency = max_concurrency
        self.tasks: Dict[str, TaskInfo] = {}
        self.active_tasks: Set[str] = set()
        self.completed_tasks: Set[str] = set()
        self.failed_tasks: Set[str] = set()
        self.semaphore = asyncio.Semaphore(max_concurrency) if max_concurrency else None
        self._task_event = asyncio.Event()
        logger.info(f"Initialized ParallelTaskManager with max_concurrency: {max_concurrency}")
    
    async def add_task(self, task_data: Dict, 
                      dependencies: Optional[List[str]] = None) -> str:
        """
        添加任务到管理器
        
        Args:
            task_data: 任务数据
            dependencies: 依赖任务ID列表
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        task_dependencies = set(dependencies) if dependencies else set()
        
        # 验证依赖任务是否存在
        for dep_id in task_dependencies:
            if dep_id not in self.tasks:
                raise ValueError(f"Dependency task {dep_id} does not exist")
        
        # 创建任务信息
        self.tasks[task_id] = TaskInfo(
            task_id=task_id,
            task_data=task_data,
            dependencies=task_dependencies
        )
        
        logger.info(f"Added task {task_id} with dependencies {task_dependencies}")
        
        # 触发任务事件，可能有新任务可以执行了
        self._task_event.set()
        
        return task_id
    
    async def execute_all(self, executor_func: Callable[[Dict], Awaitable[Dict]]) -> Dict:
        """
        执行所有任务
        
        Args:
            executor_func: 任务执行函数
            
        Returns:
            执行结果汇总
        """
        logger.info(f"Starting execution of {len(self.tasks)} tasks")
        
        # 创建执行任务
        execution_tasks = []
        for task_id, task_info in self.tasks.items():
            if not task_info.dependencies:
                # 没有依赖的任务立即执行
                execution_tasks.append(self._execute_task(task_id, executor_func))
            else:
                # 有依赖的任务等待依赖完成
                execution_tasks.append(self._execute_with_dependencies(task_id, executor_func))
        
        # 等待所有任务完成
        await asyncio.gather(*execution_tasks)
        
        # 生成结果汇总
        results = {
            "success": len(self.failed_tasks) == 0,
            "total_tasks": len(self.tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "task_results": {}
        }
        
        # 收集每个任务的结果
        for task_id, task_info in self.tasks.items():
            results["task_results"][task_id] = {
                "status": task_info.status,
                "result": task_info.result,
                "error": task_info.error,
                "dependencies": list(task_info.dependencies)
            }
        
        logger.info(f"All tasks execution completed: {results['success']}")
        return results
    
    async def _execute_with_dependencies(self, task_id: str, 
                                       executor_func: Callable[[Dict], Awaitable[Dict]]):
        """
        等待依赖完成后执行任务
        
        Args:
            task_id: 任务ID
            executor_func: 任务执行函数
        """
        task_info = self.tasks[task_id]
        
        # 等待所有依赖任务完成
        while True:
            # 检查是否所有依赖都已完成
            all_deps_completed = all(dep_id in self.completed_tasks 
                                   for dep_id in task_info.dependencies)
            
            # 检查是否有依赖任务失败
            any_dep_failed = any(dep_id in self.failed_tasks 
                                for dep_id in task_info.dependencies)
            
            if any_dep_failed:
                # 如果有依赖任务失败，标记当前任务为失败
                logger.warning(f"Task {task_id} dependency failed, marking as failed")
                task_info.status = "failed"
                task_info.error = "Dependency task failed"
                self.failed_tasks.add(task_id)
                break
            
            if all_deps_completed:
                # 所有依赖都已完成，执行任务
                await self._execute_task(task_id, executor_func)
                break
            
            # 等待任务状态变化
            self._task_event.clear()
            await self._task_event.wait()
    
    async def _execute_task(self, task_id: str, 
                           executor_func: Callable[[Dict], Awaitable[Dict]]):
        """
        执行单个任务
        
        Args:
            task_id: 任务ID
            executor_func: 任务执行函数
        """
        task_info = self.tasks[task_id]
        
        # 检查任务状态
        if task_info.status != "pending":
            logger.warning(f"Task {task_id} already {task_info.status}, skipping")
            return
        
        # 如果设置了并发限制，获取信号量
        if self.semaphore:
            await self.semaphore.acquire()
        
        try:
            # 更新任务状态为运行中
            task_info.status = "running"
            task_info.start_time = asyncio.get_event_loop().time()
            self.active_tasks.add(task_id)
            
            logger.info(f"Executing task {task_id}")
            
            # 执行任务
            result = await executor_func(task_info.task_data)
            
            # 更新任务状态为完成
            task_info.status = "completed"
            task_info.result = result
            task_info.end_time = asyncio.get_event_loop().time()
            self.active_tasks.remove(task_id)
            self.completed_tasks.add(task_id)
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            # 更新任务状态为失败
            error_msg = str(e)
            task_info.status = "failed"
            task_info.error = error_msg
            task_info.end_time = asyncio.get_event_loop().time()
            self.active_tasks.remove(task_id)
            self.failed_tasks.add(task_id)
            
            logger.error(f"Task {task_id} failed: {error_msg}")
            
        finally:
            # 释放信号量
            if self.semaphore:
                self.semaphore.release()
            
            # 触发任务事件，通知其他等待的任务
            self._task_event.set()
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否取消成功
        """
        if task_id not in self.tasks:
            logger.warning(f"Task {task_id} not found")
            return False
        
        task_info = self.tasks[task_id]
        
        # 只能取消等待中的任务
        if task_info.status == "pending":
            task_info.status = "cancelled"
            logger.info(f"Task {task_id} cancelled")
            return True
        
        logger.warning(f"Cannot cancel task {task_id} with status {task_info.status}")
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态信息
        """
        if task_id not in self.tasks:
            return None
        
        task_info = self.tasks[task_id]
        
        return {
            "task_id": task_id,
            "status": task_info.status,
            "result": task_info.result,
            "error": task_info.error,
            "dependencies": list(task_info.dependencies),
            "start_time": task_info.start_time,
            "end_time": task_info.end_time
        }
    
    def get_all_tasks_status(self) -> Dict[str, Dict]:
        """
        获取所有任务状态
        
        Returns:
            所有任务状态信息
        """
        statuses = {}
        for task_id in self.tasks:
            statuses[task_id] = self.get_task_status(task_id)
        
        return statuses
    
    def get_stats(self) -> Dict:
        """
        获取任务管理器统计信息
        
        Returns:
            统计信息
        """
        return {
            "total_tasks": len(self.tasks),
            "pending_tasks": len(self.tasks) - len(self.active_tasks) - \
                           len(self.completed_tasks) - len(self.failed_tasks),
            "active_tasks": len(self.active_tasks),
            "completed_tasks": len(self.completed_tasks),
            "failed_tasks": len(self.failed_tasks),
            "max_concurrency": self.max_concurrency,
            "current_concurrency": len(self.active_tasks)
        }
    
    async def wait_for_completion(self, task_ids: Optional[List[str]] = None):
        """
        等待指定任务完成
        
        Args:
            task_ids: 要等待的任务ID列表，如果为None则等待所有任务
        """
        if task_ids is None:
            task_ids = list(self.tasks.keys())
        
        # 检查所有任务是否都存在
        for task_id in task_ids:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")
        
        # 等待所有指定任务完成
        while True:
            all_completed = all(
                self.tasks[task_id].status in ["completed", "failed", "cancelled"]
                for task_id in task_ids
            )
            
            if all_completed:
                break
            
            # 等待任务状态变化
            self._task_event.clear()
            await self._task_event.wait()
    
    def clear_tasks(self):
        """
        清除所有任务
        """
        self.tasks.clear()
        self.active_tasks.clear()
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        logger.info("All tasks cleared")

class DynamicTaskScheduler:
    """
    动态任务调度器
    支持在运行时添加任务并根据资源情况动态调整执行
    """
    
    def __init__(self, 
                 executor_func: Callable[[Dict], Awaitable[Dict]],
                 max_concurrency: Optional[int] = None,
                 auto_execute: bool = True):
        """
        初始化动态任务调度器
        
        Args:
            executor_func: 任务执行函数
            max_concurrency: 最大并发数
            auto_execute: 是否自动执行添加的任务
        """
        self.executor_func = executor_func
        self.task_manager = ParallelTaskManager(max_concurrency)
        self.auto_execute = auto_execute
        self.execution_task: Optional[asyncio.Task] = None
        self.active = True
        
        logger.info(f"Initialized DynamicTaskScheduler with auto_execute: {auto_execute}")
        
        if self.auto_execute:
            # 启动自动执行协程
            self.execution_task = asyncio.create_task(self._auto_execute_loop())
    
    async def add_task(self, task_data: Dict, 
                      dependencies: Optional[List[str]] = None) -> str:
        """
        添加任务
        
        Args:
            task_data: 任务数据
            dependencies: 依赖任务ID列表
            
        Returns:
            任务ID
        """
        return await self.task_manager.add_task(task_data, dependencies)
    
    async def _auto_execute_loop(self):
        """
        自动执行循环
        持续检查并执行可执行的任务
        """
        while self.active:
            # 检查是否有可执行的任务（没有依赖或依赖已完成）
            executable_tasks = []
            for task_id, task_info in self.task_manager.tasks.items():
                if task_info.status == "pending" and \
                   all(dep_id in self.task_manager.completed_tasks 
                       for dep_id in task_info.dependencies):
                    executable_tasks.append(task_id)
            
            # 执行可执行的任务
            for task_id in executable_tasks:
                asyncio.create_task(
                    self.task_manager._execute_task(task_id, self.executor_func)
                )
            
            # 等待任务事件或短暂休眠
            task_event = asyncio.Event()
            
            def on_task_update():
                task_event.set()
            
            # 使用事件监听任务状态变化
            # 这里简化实现，实际可能需要更复杂的事件监听机制
            await asyncio.sleep(0.1)  # 短暂休眠避免CPU过度占用
    
    async def shutdown(self, wait: bool = True):
        """
        关闭调度器
        
        Args:
            wait: 是否等待所有任务完成
        """
        self.active = False
        
        if self.execution_task:
            self.execution_task.cancel()
            try:
                await self.execution_task
            except asyncio.CancelledError:
                pass
        
        if wait:
            # 等待所有任务完成
            all_tasks = list(self.task_manager.tasks.keys())
            if all_tasks:
                await self.task_manager.wait_for_completion(all_tasks)
        
        logger.info("DynamicTaskScheduler shutdown")

# 创建工厂函数
def create_parallel_task_manager(max_concurrency: Optional[int] = None) -> ParallelTaskManager:
    """
    创建并行任务管理器实例
    
    Args:
        max_concurrency: 最大并发数
        
    Returns:
        并行任务管理器实例
    """
    return ParallelTaskManager(max_concurrency)

def create_dynamic_task_scheduler(executor_func: Callable[[Dict], Awaitable[Dict]],
                                 max_concurrency: Optional[int] = None,
                                 auto_execute: bool = True) -> DynamicTaskScheduler:
    """
    创建动态任务调度器实例
    
    Args:
        executor_func: 任务执行函数
        max_concurrency: 最大并发数
        auto_execute: 是否自动执行添加的任务
        
    Returns:
        动态任务调度器实例
    """
    return DynamicTaskScheduler(executor_func, max_concurrency, auto_execute)
