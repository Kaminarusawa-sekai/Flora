# new/capability_actors/task_group_aggregator_actor.py
from typing import Dict, Any, List, Optional
from thespian.actors import Actor, ActorExitRequest
from ..common.messages.task_messages import (
    TaskGroupRequest, TaskCompleted, TaskFailed,
    ExecuteTaskMessage, TaskSpec, TaskGroupResult
)
import logging

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
        处理任务组请求
        
        Args:
            msg: 任务组请求消息
            sender: 消息发送者
        """
        logger.info(f"Received TaskGroupRequest: {msg.group_id}")
        
        self.reply_to = msg.reply_to
        self.group_id = msg.group_id
        
        # 为每个任务启动执行器Actor
        for task_spec in msg.tasks:
            executor_type = self._map_type_to_actor(task_spec.type)
            if executor_type:
                addr = self.createActor(executor_type)
                self.pending_tasks[addr] = task_spec.task_id
                
                # 发送执行任务消息
                execute_msg = ExecuteTaskMessage(
                    source=self.myAddress,
                    destination=addr,
                    spec=task_spec,
                    reply_to=self.myAddress
                )
                self.send(addr, execute_msg)
            else:
                # 不支持的任务类型
                logger.error(f"Unsupported task type: {task_spec.type}")
                self.failures[task_spec.task_id] = f"Unsupported task type: {task_spec.type}"

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
            
            # 创建并发送任务组结果
            result_msg = TaskGroupResult(
                source=self.myAddress,
                destination=self.reply_to,
                group_id=self.group_id,
                results=self.results,
                failures=self.failures
            )
            self.send(self.reply_to, result_msg)
            
            # 发送退出请求
            self.send(self.myAddress, ActorExitRequest())
