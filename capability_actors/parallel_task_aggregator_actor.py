# capability_actors/parallel_task_aggregator_actor.py
from typing import Dict, Any, List, Optional
from thespian.actors import Actor, ActorExitRequest
from common.messages.task_messages import (
    RepeatTaskRequest, TaskSpec, ExecuteTaskMessage,
    TaskCompleted, TaskFailed
)
import logging
from collections import Counter

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParallelTaskAggregatorActor(Actor):
    """
    并行任务聚合器Actor
    负责重复执行同一个任务并聚合结果
    """
    
    def __init__(self):
        self.spec: Optional[TaskSpec] = None
        self.reply_to: Optional[Any] = None  # 使用Any类型，因为reply_to可能是ActorAddress
        self.results: List[Any] = []
        self.failures: List[str] = []
        self.completed_runs: int = 0
        self.pending_tasks: Dict[Any, str] = {}  # actor地址 -> run_id
    
    def receiveMessage(self, msg: Any, sender: Any) -> None:
        """处理接收到的消息"""
        try:
            if isinstance(msg, RepeatTaskRequest):
                self._handle_repeat_task_request(msg, sender)
            elif isinstance(msg, TaskCompleted):
                self._handle_task_completed(msg, sender)
            elif isinstance(msg, TaskFailed):
                self._handle_task_failed(msg, sender)
        except Exception as e:
            logger.error(f"ParallelTaskAggregatorActor error: {e}")
            # 发生错误时向发起者发送失败消息
            if self.reply_to and self.spec:
                self.send(self.reply_to, TaskFailed(
                    source=self.myAddress,
                    destination=self.reply_to,
                    task_id=self.spec.task_id,
                    error=str(e),
                    details="ParallelTaskAggregatorActor system error",
                    original_spec=self.spec
                ))
                self.send(self.myAddress, ActorExitRequest())
    
    def _handle_repeat_task_request(self, msg: RepeatTaskRequest, sender: Any) -> None:
        """处理重复任务请求"""
        logger.info(f"Received RepeatTaskRequest: {msg.spec.task_id} (repeat_count: {msg.spec.repeat_count})")
        
        self.spec = msg.spec
        self.reply_to = sender  # 使用实际的sender地址
        
        # 启动 N 次独立运行
        for i in range(self.spec.repeat_count):
            run_id = f"{self.spec.task_id}_run_{i+1}"
            run_spec = TaskSpec(
                task_id=run_id,
                type=self.spec.type,
                parameters=self.spec.parameters,
                repeat_count=1,  # 防止递归
                aggregation_strategy=self.spec.aggregation_strategy
            )
            
            executor_type = self._map_type_to_actor(run_spec.type)
            if executor_type:
                executor = self.createActor(executor_type)
                self.pending_tasks[executor] = run_id
                
                # 发送执行任务消息
                execute_msg = ExecuteTaskMessage(
                    source=self.myAddress,
                    destination=executor,
                    spec=run_spec,
                    reply_to=self.myAddress
                )
                self.send(executor, execute_msg)
            else:
                # 不支持的任务类型
                logger.error(f"Unsupported task type: {run_spec.type}")
                self.failures.append(f"Unsupported task type: {run_spec.type}")
                self.completed_runs += 1
    
    def _handle_task_completed(self, msg: TaskCompleted, sender: Any) -> None:
        """处理任务完成消息"""
        logger.info(f"Received TaskCompleted: {msg.task_id}")
        
        # 移除已完成的任务
        if sender in self.pending_tasks:
            del self.pending_tasks[sender]
        
        self.results.append(msg.result)
        self.completed_runs += 1
        self._check_done()
    
    def _handle_task_failed(self, msg: TaskFailed, sender: Any) -> None:
        """处理任务失败消息"""
        logger.error(f"Received TaskFailed: {msg.task_id}, Error: {msg.error}")
        
        # 移除已完成的任务
        if sender in self.pending_tasks:
            del self.pending_tasks[sender]
        
        self.failures.append(msg.error)
        self.completed_runs += 1
        self._check_done()
    
    def _check_done(self) -> None:
        """检查是否所有任务都已完成"""
        total = self.spec.repeat_count
        if self.completed_runs >= total:
            logger.info(f"All tasks completed: {self.completed_runs}/{total}")
            # 聚合结果
            final_result = self._aggregate_results()
            
            # 如果有失败，返回失败；否则返回成功
            if self.failures:
                self.send(self.reply_to, TaskFailed(
                    source=self.myAddress,
                    destination=self.reply_to,
                    task_id=self.spec.task_id,
                    error=f"{len(self.failures)} out of {total} runs failed",
                    details=f"Failures: {self.failures}",
                    original_spec=self.spec
                ))
            else:
                self.send(self.reply_to, TaskCompleted(
                    source=self.myAddress,
                    destination=self.reply_to,
                    task_id=self.spec.task_id,
                    result=final_result,
                    original_spec=self.spec
                ))
            
            self.send(self.myAddress, ActorExitRequest())
    
    def _aggregate_results(self) -> Any:
        """聚合结果"""
        strategy = self.spec.aggregation_strategy
        logger.info(f"Aggregating results using strategy: {strategy}")
        
        if not self.results:
            return None
        
        try:
            if strategy == "list":
                return self.results
            elif strategy == "last":
                return self.results[-1]
            elif strategy == "mean":
                # 确保结果是数值类型
                numeric_results = [r for r in self.results if isinstance(r, (int, float))]
                if numeric_results:
                    return sum(numeric_results) / len(numeric_results)
                return self.results  # 如果没有数值结果，返回原始列表
            elif strategy == "majority":
                counts = Counter(self.results)
                return counts.most_common(1)[0][0] if counts else None
            elif strategy == "sum":
                # 确保结果是数值类型
                numeric_results = [r for r in self.results if isinstance(r, (int, float))]
                return sum(numeric_results) if numeric_results else 0
            elif strategy == "min":
                # 确保结果是数值类型
                numeric_results = [r for r in self.results if isinstance(r, (int, float))]
                return min(numeric_results) if numeric_results else None
            elif strategy == "max":
                # 确保结果是数值类型
                numeric_results = [r for r in self.results if isinstance(r, (int, float))]
                return max(numeric_results) if numeric_results else None
            else:
                logger.warning(f"Unknown aggregation strategy: {strategy}, defaulting to 'list'")
                return self.results  # 默认 list
        except Exception as e:
            logger.error(f"Aggregation failed: {e}, defaulting to 'list'")
            return self.results
    
    def _map_type_to_actor(self, task_type: str) -> Optional[Actor]:
        """映射任务类型到执行器Actor"""
        try:
            from .dify_actor import DifyCapabilityActor
            from .mcp_actor import MCPCapabilityActor
            from .data_actor import DataCapabilityActor
            from .memory_actor import MemoryCapabilityActor
            
            actor_map = {
                "dify": DifyCapabilityActor,
                "mcp": MCPCapabilityActor,
                "data": DataCapabilityActor,
                "memory": MemoryCapabilityActor,
            }
            
            return actor_map.get(task_type)
        except ImportError as e:
            logger.error(f"Failed to import actor classes: {e}")
            return None
