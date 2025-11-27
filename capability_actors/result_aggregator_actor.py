# new/agents/execution/result_aggregator.py
from typing import Dict, Any, List, Optional, Set
from thespian.actors import Actor
import logging
from datetime import datetime
from capabilities.result_aggregation.result_aggregation import ResultAggregator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class ResultAggregatorActor(Actor):
    """
    Result Aggregator Actor - 用于聚合子任务结果的临时Actor
    
    核心职责：
    1. 接收并跟踪子任务结果
    2. 聚合结果并返回给发起者
    3. 支持重试逻辑
    4. 维护任务上下文和跟踪信息
    
    设计原则：
    - 仅对直接子任务负责
    - 结果由发起者收集
    - 重试逻辑靠近失败点
    - 避免全局上下文
    """
    
    def __init__(self):
        self._pending_tasks: Dict[str, Any] = {}  # task_id -> task_info
        self._completed_tasks: Dict[str, Any] = {}  # task_id -> result
        self._failed_tasks: Dict[str, Any] = {}  # task_id -> error_info
        self._retries: Dict[str, int] = {}  # task_id -> retry_count
        self._max_retries = 3  # 默认最大重试次数
        self._timeout = 300  # 默认超时时间（秒）
        self._creator: Any = None  # 发起者Actor地址
        self._aggregation_strategy: str = "map_reduce"  # 默认聚合策略
        self._trace_id: str = None  # 用于跟踪的trace_id
    
    def receiveMessage(self, message: Any, sender: Any) -> None:
        """处理接收到的消息"""
        try:
            if isinstance(message, dict):
                msg_type = message.get("type")
                
                if msg_type == "initialize":
                    self._handle_initialize(message, sender)
                elif msg_type == "add_subtask":
                    self._handle_add_subtask(message, sender)
                elif msg_type == "subtask_result":
                    self._handle_subtask_result(message, sender)
                elif msg_type == "subtask_error":
                    self._handle_subtask_error(message, sender)
                elif msg_type == "aggregator_result":
                    self._handle_aggregator_result(message, sender)
                elif msg_type == "aggregator_error":
                    self._handle_aggregator_error(message, sender)
                elif msg_type == "get_final_result":
                    self._handle_get_final_result(message, sender)
                else:
                    logger.warning(f"Unknown message type: {msg_type}")
            elif isinstance(message, (SubtaskResultMessage, SubtaskErrorMessage)):
                # 向后兼容：直接处理结果/错误消息
                if hasattr(message, "task_id") and hasattr(message, "result"):
                    self._handle_subtask_result(message.__dict__, sender)
                elif hasattr(message, "task_id") and hasattr(message, "error"):
                    self._handle_subtask_error(message.__dict__, sender)
                else:
                    logger.warning(f"Unknown message format: {type(message)}")
            else:
                logger.warning(f"Unknown message type: {type(message)}")
        except Exception as e:
            logger.error(f"ResultAggregatorActor execution failed: {e}")
            self._send_error_to_creator(str(e))
    
    def _handle_initialize(self, msg: Dict[str, Any], sender: Any) -> None:
        """初始化聚合器"""
        self._creator = sender
        self._trace_id = msg.get("trace_id", f"trace_{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}")
        self._max_retries = msg.get("max_retries", self._max_retries)
        self._timeout = msg.get("timeout", self._timeout)
        self._aggregation_strategy = msg.get("aggregation_strategy", self._aggregation_strategy)
        self._reduce_func = msg.get("reduce_func")
        
        # 处理初始的待处理任务
        pending_tasks = msg.get("pending_tasks", [])
        if pending_tasks:
            for task_id in pending_tasks:
                self._pending_tasks[task_id] = {}
                self._retries[task_id] = 0
            logger.info(f"Added {len(pending_tasks)} initial pending tasks to aggregator")
        
        logger.info(f"ResultAggregatorActor initialized with trace_id: {self._trace_id}")
    
    def _handle_add_subtask(self, msg: Dict[str, Any], sender: Any) -> None:
        """添加子任务"""
        task_id = msg.get("task_id")
        task_info = msg.get("task_info", {})
        
        if not task_id:
            logger.warning("Subtask without task_id received")
            return
        
        self._pending_tasks[task_id] = task_info
        self._retries[task_id] = 0
        logger.info(f"Added subtask {task_id} to aggregator")
    
    def _handle_subtask_result(self, msg: Dict[str, Any], sender: Any) -> None:
        """处理子任务成功结果"""
        task_id = msg.get("task_id")
        result = msg.get("result", {})
        
        if not task_id:
            logger.warning("Result without task_id received")
            return
        
        if task_id in self._pending_tasks:
            del self._pending_tasks[task_id]
            
        if task_id in self._failed_tasks:
            del self._failed_tasks[task_id]
            
        self._completed_tasks[task_id] = result
        logger.info(f"Received successful result for subtask {task_id}")
        
        # 检查是否所有任务都已完成
        self._check_completion()
    
    def _handle_subtask_error(self, msg: Dict[str, Any], sender: Any) -> None:
        """处理子任务失败"""
        task_id = msg.get("task_id")
        error = msg.get("error", "Unknown error")
        
        if not task_id:
            logger.warning("Error without task_id received")
            return
        
        retry_count = self._retries.get(task_id, 0)
        
        if retry_count < self._max_retries:
            # 重试任务
            self._retries[task_id] = retry_count + 1
            logger.info(f"Retrying task {task_id} (attempt {retry_count + 1}/{self._max_retries})")
            
            # 向子任务执行器发送重试请求
            retry_msg = {
                "type": "retry_subtask",
                "task_id": task_id,
                "trace_id": self._trace_id,
                "retry_count": retry_count + 1
            }
            # 发送给任务执行器（假设sender是执行器）
            self.send(sender, retry_msg)
        else:
            # 超过最大重试次数
            logger.error(f"Task {task_id} failed after {self._max_retries} attempts: {error}")
            self._failed_tasks[task_id] = error
            
            if task_id in self._pending_tasks:
                del self._pending_tasks[task_id]
            
            # 检查是否所有任务都已完成
            self._check_completion()
    
    def _handle_aggregator_result(self, msg: Dict[str, Any], sender: Any) -> None:
        """处理子聚合器的结果（用于嵌套聚合）"""
        aggregator_id = msg.get("aggregator_id")
        result = msg.get("result", {})
        
        # 将子聚合器的结果视为一个普通子任务结果处理
        self._handle_subtask_result({"task_id": aggregator_id, "result": result}, sender)
    
    def _handle_aggregator_error(self, msg: Dict[str, Any], sender: Any) -> None:
        """处理子聚合器的错误（用于嵌套聚合）"""
        aggregator_id = msg.get("aggregator_id")
        error = msg.get("error", "Unknown error")
        
        # 将子聚合器的错误视为一个普通子任务错误处理
        self._handle_subtask_error({"task_id": aggregator_id, "error": error}, sender)
    
    def _handle_get_final_result(self, msg: Dict[str, Any], sender: Any) -> None:
        """处理获取最终结果的请求"""
        logger.info(f"Received get_final_result request with trace_id: {msg.get('trace_id')}")
        
        # 检查是否有未完成的任务
        if self._pending_tasks:
            # 如果有未完成的任务，返回当前状态
            logger.info(f"There are still pending tasks: {list(self._pending_tasks.keys())}")
            self.send(sender, {
                "type": "aggregation_in_progress",
                "trace_id": self._trace_id,
                "pending_tasks": list(self._pending_tasks.keys()),
                "completed_tasks": len(self._completed_tasks),
                "failed_tasks": len(self._failed_tasks),
                "total_tasks": len(self._pending_tasks) + len(self._completed_tasks) + len(self._failed_tasks)
            })
        else:
            # 如果所有任务都已完成，执行聚合并返回结果
            logger.info(f"All tasks completed. Calculating final result")
            aggregated_result = self._aggregate_results()
            
            self.send(sender, {
                "type": "aggregation_complete",
                "trace_id": self._trace_id,
                "success": len(self._failed_tasks) == 0,
                "aggregated_result": aggregated_result,
                "completed_tasks": self._completed_tasks,
                "failed_tasks": self._failed_tasks,
                "total_tasks": len(self._completed_tasks) + len(self._failed_tasks),
                "strategy": self._aggregation_strategy
            })
    
    def _check_completion(self) -> None:
        """检查是否所有任务都已完成"""
        if not self._pending_tasks and (self._completed_tasks or self._failed_tasks):
            logger.info(f"All tasks completed. Completed: {len(self._completed_tasks)}, Failed: {len(self._failed_tasks)}")
            
            # 执行聚合
            aggregated_result = self._aggregate_results()
            
            # 将结果返回给发起者
            result_msg = {
                "type": "aggregation_complete",
                "trace_id": self._trace_id,
                "success": len(self._failed_tasks) == 0,
                "aggregated_result": aggregated_result,
                "completed_tasks": self._completed_tasks,
                "failed_tasks": self._failed_tasks,
                "total_tasks": len(self._completed_tasks) + len(self._failed_tasks),
                "strategy": self._aggregation_strategy
            }
            
            self.send(self._creator, result_msg)
            logger.info(f"Aggregation completed. Sending result to creator")
    
    def _aggregate_results(self) -> Dict[str, Any]:
        """聚合所有结果"""
        if not self._completed_tasks:
            return {
                "success": False,
                "error": "No successful tasks",
                "failed_tasks": len(self._failed_tasks),
                "total_tasks": len(self._failed_tasks)
            }
        
        # 获取所有成功结果
        results = list(self._completed_tasks.values())
        
        # 使用ResultAggregator的聚合逻辑
        if self._aggregation_strategy == "map_reduce":
            if self._reduce_func:
                return self._reduce_func(results)
            else:
                return ResultAggregator._default_reduce(results)
        elif self._aggregation_strategy == "sequential":
            return self._aggregate_sequential(results)
        elif self._aggregation_strategy == "vote":
            return self._aggregate_vote(results)
        else:
            # 默认使用map_reduce
            if self._reduce_func:
                return self._reduce_func(results)
            else:
                return ResultAggregator._default_reduce(results)
    
    def _aggregate_sequential(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """顺序聚合结果（取最后一个结果）"""
        if not results:
            return {"success": False, "error": "No results to aggregate"}
        
        return results[-1]
    
    def _aggregate_vote(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """投票聚合结果（简单多数）"""
        if not results:
            return {"success": False, "error": "No results to aggregate"}
        
        # 简单实现：计算每个结果的出现次数
        from collections import Counter
        
        # 假设结果包含一个"output"字段
        outputs = [r.get("output", "unknown") for r in results]
        counts = Counter(outputs)
        
        # 找出出现次数最多的结果
        most_common = counts.most_common(1)
        if most_common:
            return {
                "success": True,
                "output": most_common[0][0],
                "vote_counts": dict(counts),
                "total_votes": len(results)
            }
        else:
            return {"success": False, "error": "Vote aggregation failed"}
    
    def _send_error_to_creator(self, error: str) -> None:
        """向发起者发送错误消息"""
        if self._creator:
            error_msg = {
                "type": "aggregation_error",
                "trace_id": self._trace_id,
                "error": error,
                "completed_tasks": self._completed_tasks,
                "failed_tasks": self._failed_tasks
            }
            self.send(self._creator, error_msg)
    
    def _should_retry(self, task_id: str) -> bool:
        """检查是否应该重试任务"""
        return task_id in self._retries and self._retries[task_id] < self._max_retries


# 为了向后兼容，导入常见的消息类型
class SubtaskResultMessage:
    """子任务成功结果消息"""
    def __init__(self, task_id: str, result: Dict[str, Any]):
        self.task_id = task_id
        self.result = result

class SubtaskErrorMessage:
    """子任务失败错误消息"""
    def __init__(self, task_id: str, error: str):
        self.task_id = task_id
        self.error = error