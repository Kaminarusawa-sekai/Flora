# capability_actors/task_group_aggregator_actor.py
from typing import Dict, Any, List, Optional
from thespian.actors import Actor, ActorExitRequest
from common.messages.task_messages import (
    TaskGroupRequest, TaskCompleted, TaskFailed,
    ExecuteTaskMessage, TaskSpec, TaskGroupResult
)
import logging

# 导入事件总线
from events.event_bus import event_bus
from events.event_types import EventType

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskGroupAggregatorActor(Actor):
    """
    任务组聚合器Actor
    负责执行一组任务并聚合结果
    支持任务重试和错误处理
    """
    
    def __init__(self):
        """
        初始化任务组聚合器
        """
        super().__init__()
        self.pending_tasks: Dict[Actor, str] = {}  # actor_addr -> task_id
        self.results: Dict[str, Any] = {}  # task_id -> result
        self.failures: Dict[str, str] = {}  # task_id -> error
        self.reply_to: Optional[str] = None
        self.max_retries: int = 2  # 默认最大重试次数
        self.retry_count: Dict[str, int] = {}  # task_id -> retry_count
        self.group_id: Optional[str] = None

    def receiveMessage(self, msg: Any, sender: Actor) -> None:
        """
        处理接收到的消息
        
        Args:
            msg: 收到的消息
            sender: 消息发送者
        """
        try:
            if isinstance(msg, TaskGroupRequest):
                self._handle_task_group_request(msg, sender)
            elif isinstance(msg, TaskCompleted):
                self._handle_task_completed(msg, sender)
            elif isinstance(msg, TaskFailed):
                self._handle_task_failed(msg, sender)
        except Exception as e:
            logger.error(f"TaskGroupAggregatorActor error: {e}")
            # 发生错误时向发起者发送失败消息
            if self.reply_to and self.group_id:
                self.send(self.reply_to, TaskGroupResult(
                    source=self.myAddress,
                    destination=self.reply_to,
                    group_id=self.group_id,
                    results=self.results,
                    failures={**self.failures, "system_error": str(e)}
                ))
                self.send(self.myAddress, ActorExitRequest())

    def _handle_task_group_request(self, msg: TaskGroupRequest, sender: Actor) -> None:
        """
        ⑧ 组任务管理 - 判断是否需要并行执行

        Args:
            msg: 任务组请求消息
            sender: 消息发送者
        """
        logger.info(f"Received TaskGroupRequest: {msg.group_id}")

        self.reply_to = msg.reply_to
        self.group_id = msg.group_id

        # ⑨ 判断是否需要并行执行
        needs_parallel = self._should_use_parallel_execution(msg.tasks)

        if needs_parallel:
            # 使用并行执行
            logger.info(f"⑨ 并行执行判断: 任务组 {msg.group_id} 需要并行优化")
            self._dispatch_to_parallel_aggregator(msg)
        else:
            # 使用普通结果聚合
            logger.info(f"⑨ 并行执行判断: 任务组 {msg.group_id} 使用标准执行")
            self._dispatch_to_result_aggregator(msg)

    def _should_use_parallel_execution(self, tasks: List[TaskSpec]) -> bool:
        """
        ⑨ 判断是否需要并行执行

        判断逻辑：
        1. 如果任务需要多次执行（repeat_count > 1）
        2. 如果参数中明确指定需要优化
        3. 如果聚合策略需要多次执行（mean、majority等）

        Args:
            tasks: 任务列表

        Returns:
            是否需要并行执行
        """
        for task in tasks:
            # 检查是否需要重复执行
            if task.repeat_count and task.repeat_count > 1:
                return True

            # 检查聚合策略
            if task.aggregation_strategy in ["mean", "majority", "sum", "min", "max"]:
                return True

            # 检查参数中的优化标志
            if isinstance(task.parameters, dict):
                if task.parameters.get("needs_optimization", False):
                    return True
                if "optimization_params" in task.parameters:
                    return True

        return False

    def _dispatch_to_parallel_aggregator(self, msg: TaskGroupRequest) -> None:
        """
        分发给并行任务聚合器

        Args:
            msg: 任务组请求消息
        """
        from capability_actors.parallel_task_aggregator_actor import ParallelTaskAggregatorActor
        from common.messages.task_messages import RepeatTaskRequest

        # 为每个任务创建并行聚合器
        for task_spec in msg.tasks:
            parallel_aggregator = self.createActor(ParallelTaskAggregatorActor)
            self.pending_tasks[parallel_aggregator] = task_spec.task_id

            # 发送重复任务请求
            repeat_request = RepeatTaskRequest(
                source=self.myAddress,
                destination=parallel_aggregator,
                spec=task_spec
            )
            self.send(parallel_aggregator, repeat_request)

            # 发布事件
            event_bus.publish_task_event(
                task_id=task_spec.task_id,
                event_type=EventType.PARALLEL_EXECUTION_STARTED.value,
                source="TaskGroupAggregatorActor",
                agent_id="system",
                data={
                    "repeat_count": task_spec.repeat_count,
                    "aggregation_strategy": task_spec.aggregation_strategy
                }
            )

    def _dispatch_to_result_aggregator(self, msg: TaskGroupRequest) -> None:
        """
        ⑩ 分发给结果聚合器进行单任务执行

        Args:
            msg: 任务组请求消息
        """
        from capability_actors.result_aggregator_actor import ResultAggregatorActor

        # 创建结果聚合器
        result_aggregator = self.createActor(ResultAggregatorActor)

        # 初始化聚合器
        init_msg = {
            "type": "initialize",
            "trace_id": msg.group_id,
            "max_retries": 3,
            "timeout": 300,
            "aggregation_strategy": "map_reduce",
            "pending_tasks": [task.task_id for task in msg.tasks]
        }
        self.send(result_aggregator, init_msg)

        # 记录聚合器
        self.pending_tasks[result_aggregator] = msg.group_id

        # 为每个任务发送执行请求到结果聚合器
        for task_spec in msg.tasks:
            execute_msg = {
                "type": "execute_subtask",
                "task_id": task_spec.task_id,
                "task_spec": task_spec,
                "capability": task_spec.type,
                "parameters": task_spec.parameters
            }
            self.send(result_aggregator, execute_msg)

    def _handle_task_completed(self, msg: TaskCompleted, sender: Actor) -> None:
        """
        处理任务完成消息
        
        Args:
            msg: 任务完成消息
            sender: 消息发送者
        """
        logger.info(f"Received TaskCompleted: {msg.task_id}")
        
        task_id = self.pending_tasks.get(sender)
        if task_id:
            self.results[task_id] = msg.result
            # 移除已完成的任务
            del self.pending_tasks[sender]
            self._check_done()
        else:
            logger.warning(f"TaskCompleted from unknown sender: {sender}")

    def _handle_task_failed(self, msg: TaskFailed, sender: Actor) -> None:
        """
        处理任务失败消息
        
        Args:
            msg: 任务失败消息
            sender: 消息发送者
        """
        logger.info(f"Received TaskFailed: {msg.task_id}, error: {msg.error}")
        
        task_id = self.pending_tasks.get(sender)
        if task_id:
            if self._should_retry(task_id):
                self._retry_task(task_id, msg.original_spec)
            else:
                self.failures[task_id] = msg.error
                # 移除已失败的任务
                del self.pending_tasks[sender]
                self._check_done()
        else:
            logger.warning(f"TaskFailed from unknown sender: {sender}")

    def _map_type_to_actor(self, task_type: str) -> Optional[type]:
        """
        将任务类型映射到对应的Actor类
        
        Args:
            task_type: 任务类型
            
        Returns:
            对应的Actor类或None
        """
        from capability_actors.dify_actor import DifyCapabilityActor
        from capability_actors.mcp_actor import MCPCapabilityActor
        from capability_actors.data_actor import DataActor
        mapping = {
            "dify": DifyCapabilityActor,
            "mcp": MCPCapabilityActor,
            "data": DataActor
        }
        return mapping.get(task_type)

    def _should_retry(self, task_id: str) -> bool:
        """
        检查是否应该重试任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否应该重试
        """
        current_retry = self.retry_count.get(task_id, 0)
        return current_retry < self.max_retries

    def _retry_task(self, task_id: str, spec: Optional[TaskSpec]) -> None:
        """
        重试任务
        
        Args:
            task_id: 任务ID
            spec: 任务规范
        """
        if not spec:
            logger.error(f"Cannot retry task {task_id}: no spec provided")
            self.failures[task_id] = "No spec for retry"
            # 从pending_tasks中移除任何与此任务相关的条目
            for addr, pending_task_id in list(self.pending_tasks.items()):
                if pending_task_id == task_id:
                    del self.pending_tasks[addr]
            self._check_done()
            return
            
        logger.info(f"Retrying task {task_id} (attempt {self.retry_count.get(task_id, 0) + 1}/{self.max_retries})")
        
        # 更新重试计数
        self.retry_count[task_id] = self.retry_count.get(task_id, 0) + 1
        
        # 创建新的执行器Actor
        executor_type = self._map_type_to_actor(spec.type)
        if not executor_type:
            logger.error(f"Cannot retry task {task_id}: unsupported type")
            self.failures[task_id] = "Unsupported task type for retry"
            # 从pending_tasks中移除任何与此任务相关的条目
            for addr, pending_task_id in list(self.pending_tasks.items()):
                if pending_task_id == task_id:
                    del self.pending_tasks[addr]
            self._check_done()
            return
            
        new_addr = self.createActor(executor_type)
        self.pending_tasks[new_addr] = task_id
        
        # 发送执行消息
        execute_msg = ExecuteTaskMessage(
            source=self.myAddress,
            destination=new_addr,
            spec=spec,
            reply_to=self.myAddress
        )
        self.send(new_addr, execute_msg)

    def _check_done(self) -> None:
        """
        检查所有任务是否完成
        """
        total_tasks = len(self.pending_tasks) + len(self.results) + len(self.failures)
        completed_tasks = len(self.results) + len(self.failures)

        logger.info(f"TaskGroup {self.group_id}: {completed_tasks}/{total_tasks} tasks completed")

        if completed_tasks >= total_tasks and self.reply_to and self.group_id:
            logger.info(f"All tasks for group {self.group_id} completed")

            # 发布任务组完成事件
            if self.failures:
                event_bus.publish_task_event(
                    task_id=self.group_id,
                    event_type=EventType.TASK_FAILED.value,
                    source="TaskGroupAggregatorActor",
                    agent_id="system",
                    data={
                        "total_tasks": total_tasks,
                        "completed_tasks": completed_tasks,
                        "failures": self.failures
                    }
                )
            else:
                event_bus.publish_task_event(
                    task_id=self.group_id,
                    event_type=EventType.TASK_COMPLETED.value,
                    source="TaskGroupAggregatorActor",
                    agent_id="system",
                    data={
                        "total_tasks": total_tasks,
                        "completed_tasks": completed_tasks,
                        "results": self.results
                    }
                )

            # 发送任务组结果 - 以字典格式发送以匹配ExecutionActor的期望
            result_msg = {
                "type": "task_group_result",
                "group_id": self.group_id,
                "results": self.results,
                "failures": self.failures,
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks
            }
            self.send(self.reply_to, result_msg)

            # 发送退出请求
            self.send(self.myAddress, ActorExitRequest())
