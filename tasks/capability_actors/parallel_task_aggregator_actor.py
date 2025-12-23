# capability_actors/parallel_task_aggregator_actor.py
from typing import Dict, Any, List, Optional
from thespian.actors import Actor, ActorExitRequest
from common.messages.task_messages import (
    ParallelTaskRequestMessage, TaskSpec, ExecuteTaskMessage,
    TaskCompletedMessage
)
from common.messages.types import MessageType
import logging
from collections import Counter

# 导入事件总线
from events.event_bus import event_bus
from common.event import EventType

# 导入优化相关组件
from capabilities.parallel import OptimizationOrchestrator
from capabilities.dimension.dimension_parser import DimensionParserCapability

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ParallelTaskAggregatorActor(Actor):
    """
    并行任务聚合器Actor
    负责重复执行同一个任务并聚合结果

    支持两种模式：
    1. 简单重复执行模式：多次执行相同任务，聚合结果
    2. 优化模式：使用Optuna+LLM自动优化任务参数
    """

    def __init__(self):
        self.spec: Optional[TaskSpec] = None
        self.reply_to: Optional[Any] = None  # 使用Any类型，因为reply_to可能是ActorAddress
        self.results: List[Any] = []
        self.failures: List[str] = []
        self.completed_runs: int = 0
        self.pending_tasks: Dict[Any, str] = {}  # actor地址 -> run_id

        # 优化相关
        self.optimization_enabled: bool = False
        self.orchestrator: Optional[OptimizationOrchestrator] = None
        self.current_batch_trials: List[Dict[str, Any]] = []  # 当前批次的trials
        self.optimization_results: List[Dict[str, Any]] = []  # 优化结果历史
        self.max_optimization_rounds: int = 5  # 最大优化轮数
        self.current_round: int = 0
    
    def receiveMessage(self, msg: Any, sender: Any) -> None:
        """处理接收到的消息"""
        try:
            if isinstance(msg, ParallelTaskRequestMessage):
                self._handle_repeat_task_request(msg, sender)
            elif isinstance(msg, TaskCompletedMessage):
                if msg.status in ["SUCCESS"]:
                    self._handle_task_completed(msg, sender)
                elif msg.status in ["FAILED", "ERROR", "CANCELLED"]:
                    self._handle_task_failed(msg, sender)
        except Exception as e:
            logger.error(f"ParallelTaskAggregatorActor error: {e}")
            # 发生错误时向发起者发送失败消息
            if self.reply_to and self.spec:
                self.send(self.reply_to, TaskCompletedMessage(
                    message_type=MessageType.TASK_COMPLETED,
                    source=str(self.myAddress),
                    destination=str(self.reply_to),
                    task_id=self.spec.task_id,
                    trace_id=self.spec.task_id,
                    task_path="/",
                    result=None,
                    status="FAILED",
                    agent_id=None
                ))
                self.send(self.myAddress, ActorExitRequest())
    
    def _handle_repeat_task_request(self, msg: ParallelTaskRequestMessage, sender: Any) -> None:
        """
        处理重复任务请求

        支持两种模式：
        1. 简单重复执行：直接执行N次
        2. 优化模式：使用Optuna+LLM优化参数
        """
        logger.info(f"Received ParallelTaskRequestMessage: {msg.spec.task_id} (repeat_count: {msg.spec.repeat_count})")

        self.spec = msg.spec
        self.reply_to = sender  # 使用实际的sender地址

        # 检查是否启用优化
        self.optimization_enabled = msg.spec.parameters.get("optimization_enabled", False)
        user_goal = msg.spec.parameters.get("user_goal", "")

        if self.optimization_enabled and user_goal:
            logger.info(f"Optimization mode enabled for task {msg.spec.task_id}")
            self._handle_optimization_mode(user_goal)
        else:
            logger.info(f"Simple repeat mode for task {msg.spec.task_id}")
            self._handle_simple_repeat_mode()

    def _handle_simple_repeat_mode(self) -> None:
        """简单重复执行模式：多次执行相同任务"""
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

    def _handle_optimization_mode(self, user_goal: str) -> None:
        """
        优化模式：使用Optuna+LLM自动优化任务参数

        流程:
        1. 使用DimensionParser发现优化维度
        2. 使用OptimizationOrchestrator生成优化指令批次
        3. 执行指令并收集结果
        4. 评估结果并更新优化器
        5. 重复2-4直到达到最大轮数
        """
        try:
            # 1. 创建优化协调器
            direction = self.spec.parameters.get("optimization_direction", "maximize")
            batch_size = min(self.spec.repeat_count, self.spec.parameters.get("batch_size", 3))

            self.orchestrator = OptimizationOrchestrator(
                user_goal=user_goal,
                direction=direction,
                max_concurrent=batch_size
            )

            # 2. 发现优化维度
            logger.info(f"Discovering optimization dimensions for goal: {user_goal}")
            schema = self.orchestrator.discover_optimization_dimensions()

            logger.info(f"Discovered {len(schema['dimensions'])} dimensions: {schema['dimensions']}")

            # 发布优化启动事件
            event_bus.publish_task_event(
                task_id=self.spec.task_id,
                event_type=EventType.OPTIMIZATION_STARTED.value,
                source="ParallelTaskAggregatorActor",
                agent_id="system",
                data={
                    "user_goal": user_goal,
                    "dimensions": schema['dimensions'],
                    "batch_size": batch_size
                }
            )

            # 3. 启动第一轮优化
            self._start_optimization_round(batch_size)

        except Exception as e:
            logger.error(f"Failed to initialize optimization mode: {e}")
            # 降级到简单重复模式
            self.optimization_enabled = False
            self._handle_simple_repeat_mode()

    def _start_optimization_round(self, batch_size: int) -> None:
        """启动一轮优化"""
        self.current_round += 1
        logger.info(f"Starting optimization round {self.current_round}/{self.max_optimization_rounds}")

        try:
            # 获取优化指令批次
            batch_data = self.orchestrator.get_optimization_instructions(batch_size)
            self.current_batch_trials = batch_data['trials']

            logger.info(f"Generated {len(self.current_batch_trials)} optimization instructions")

            # 为每个trial执行任务
            for trial_data in self.current_batch_trials:
                trial_number = trial_data['trial_number']
                instruction = trial_data['instruction']
                vector = trial_data['vector']

                # 创建执行规范
                run_id = f"{self.spec.task_id}_trial_{trial_number}"
                run_params = self.spec.parameters.copy()
                run_params['optimization_instruction'] = instruction
                run_params['optimization_vector'] = vector
                run_params['trial_number'] = trial_number

                run_spec = TaskSpec(
                    task_id=run_id,
                    type=self.spec.type,
                    parameters=run_params,
                    repeat_count=1,
                    aggregation_strategy="single"
                )

                # 执行任务
                executor_type = self._map_type_to_actor(run_spec.type)
                if executor_type:
                    executor = self.createActor(executor_type)
                    self.pending_tasks[executor] = run_id

                    execute_msg = ExecuteTaskMessage(
                        source=self.myAddress,
                        destination=executor,
                        spec=run_spec,
                        reply_to=self.myAddress
                    )
                    self.send(executor, execute_msg)

                    logger.info(f"Dispatched trial {trial_number} with instruction: {instruction[:100]}...")
                else:
                    logger.error(f"Unsupported task type: {run_spec.type}")
                    self.failures.append(f"Unsupported task type for trial {trial_number}")
                    self.completed_runs += 1

        except Exception as e:
            logger.error(f"Failed to start optimization round: {e}")
            self._finalize_optimization()
    
    def _handle_task_completed(self, msg: TaskCompletedMessage, sender: Any) -> None:
        """处理任务完成消息"""
        logger.info(f"Received TaskCompletedMessage: {msg.task_id}")
        
        # 移除已完成的任务
        if sender in self.pending_tasks:
            del self.pending_tasks[sender]
        
        self.results.append(msg.result)
        self.completed_runs += 1
        self._check_done()
    
    def _handle_task_failed(self, msg: TaskCompletedMessage, sender: Any) -> None:
        """处理任务失败消息"""
        error = msg.error if hasattr(msg, 'error') and msg.error else "Unknown error"
        logger.error(f"Received TaskCompletedMessage (failed): {msg.task_id}, Error: {error}")
        
        # 移除已完成的任务
        if sender in self.pending_tasks:
            del self.pending_tasks[sender]
        
        self.failures.append(error)
        self.completed_runs += 1
        self._check_done()
    
    def _check_done(self) -> None:
        """检查是否所有任务都已完成"""
        if self.optimization_enabled:
            # 优化模式：检查当前批次是否完成
            self._check_optimization_batch_done()
        else:
            # 简单重复模式：检查所有任务是否完成
            self._check_simple_repeat_done()

    def _check_simple_repeat_done(self) -> None:
        """检查简单重复模式是否完成"""
        total = self.spec.repeat_count
        if self.completed_runs >= total:
            logger.info(f"All tasks completed: {self.completed_runs}/{total}")
            # 聚合结果
            final_result = self._aggregate_results()

            # 发布并行执行完成事件
            if self.failures:
                event_bus.publish_task_event(
                    task_id=self.spec.task_id,
                    event_type=EventType.PARALLEL_EXECUTION_COMPLETED.value,
                    source="ParallelTaskAggregatorActor",
                    agent_id="system",
                    data={
                        "success": False,
                        "total_runs": total,
                        "successful_runs": len(self.results),
                        "failed_runs": len(self.failures),
                        "aggregation_strategy": self.spec.aggregation_strategy
                    }
                )
                # 有失败，返回失败消息
                error = f"{len(self.failures)} out of {total} runs failed"
                result_msg = TaskCompletedMessage(
                    message_type=MessageType.TASK_COMPLETED,
                    source=str(self.myAddress),
                    destination=str(self.reply_to),
                    task_id=self.spec.task_id,
                    trace_id=self.spec.task_id,
                    task_path="/",
                    result=final_result,
                    status="FAILED",
                    agent_id=None
                )
            else:
                event_bus.publish_task_event(
                    task_id=self.spec.task_id,
                    event_type=EventType.PARALLEL_EXECUTION_COMPLETED.value,
                    source="ParallelTaskAggregatorActor",
                    agent_id="system",
                    data={
                        "success": True,
                        "total_runs": total,
                        "successful_runs": len(self.results),
                        "aggregation_strategy": self.spec.aggregation_strategy,
                        "result": final_result
                    }
                )
                # 所有任务成功
                result_msg = TaskCompletedMessage(
                    message_type=MessageType.TASK_COMPLETED,
                    source=str(self.myAddress),
                    destination=str(self.reply_to),
                    task_id=self.spec.task_id,
                    trace_id=self.spec.task_id,
                    task_path="/",
                    result=final_result,
                    status="SUCCESS",
                    agent_id=None
                )

            self.send(self.reply_to, result_msg)
            self.send(self.myAddress, ActorExitRequest())

    def _check_optimization_batch_done(self) -> None:
        """检查优化批次是否完成"""
        batch_size = len(self.current_batch_trials)

        # 检查当前批次是否完成
        if self.completed_runs >= batch_size:
            logger.info(f"Optimization batch {self.current_round} completed: {self.completed_runs}/{batch_size}")

            try:
                # 处理优化结果
                self._process_optimization_results()

                # 重置计数器为下一轮准备
                self.completed_runs = 0
                self.results = []
                self.failures = []

                # 检查是否继续优化
                if self.current_round < self.max_optimization_rounds:
                    # 启动下一轮优化
                    batch_size = min(
                        self.spec.repeat_count,
                        self.spec.parameters.get("batch_size", 3)
                    )
                    self._start_optimization_round(batch_size)
                else:
                    # 优化完成
                    self._finalize_optimization()

            except Exception as e:
                logger.error(f"Failed to process optimization results: {e}")
                self._finalize_optimization()

    def _process_optimization_results(self) -> None:
        """处理优化结果并更新优化器"""
        logger.info(f"Processing {len(self.results)} optimization results")

        # 准备结果数据
        trial_results = []
        for i, result in enumerate(self.results):
            if i < len(self.current_batch_trials):
                trial_data = self.current_batch_trials[i]
                trial_number = trial_data['trial_number']

                # 提取输出内容
                output = str(result) if result else ""

                trial_results.append({
                    'trial_number': trial_number,
                    'output': output,
                    'result': result
                })

        # 使用orchestrator处理结果
        update_result = self.orchestrator.process_execution_results(trial_results)

        # 保存优化历史
        self.optimization_results.append({
            'round': self.current_round,
            'results': trial_results,
            'best_params': update_result.get('best_params'),
            'trial_count': update_result.get('trial_count')
        })

        logger.info(f"Optimization round {self.current_round} processed. Best params: {update_result.get('best_params')}")

        # 发布优化进度事件
        event_bus.publish_task_event(
            task_id=self.spec.task_id,
            event_type=EventType.OPTIMIZATION_TRIGGERED.value,
            source="ParallelTaskAggregatorActor",
            agent_id="system",
            data={
                "round": self.current_round,
                "best_params": update_result.get('best_params'),
                "trial_count": update_result.get('trial_count')
            }
        )

    def _finalize_optimization(self) -> None:
        """完成优化流程并返回最佳结果"""
        logger.info(f"Finalizing optimization after {self.current_round} rounds")

        try:
            # 获取最佳参数
            best_params = self.orchestrator.get_best_parameters() if self.orchestrator else None
            optimization_history = self.orchestrator.optimizer.get_optimization_history() if self.orchestrator else []

            # 构建最终结果
            optimization_result = {
                "best_parameters": best_params,
                "optimization_history": optimization_history,
                "total_rounds": self.current_round,
                "total_trials": len(optimization_history)
            }

            # 发布优化完成事件
            event_bus.publish_task_event(
                task_id=self.spec.task_id,
                event_type=EventType.OPTIMIZATION_COMPLETED.value,
                source="ParallelTaskAggregatorActor",
                agent_id="system",
                data={
                    "best_parameters": best_params,
                    "total_rounds": self.current_round,
                    "total_trials": len(optimization_history)
                }
            )

            logger.info(f"Optimization completed. Best value: {best_params.get('value') if best_params else 'N/A'}")

            # 创建成功的 TaskCompletedMessage
            result_msg = TaskCompletedMessage(
                message_type=MessageType.TASK_COMPLETED,
                source=str(self.myAddress),
                destination=str(self.reply_to),
                task_id=self.spec.task_id,
                trace_id=self.spec.task_id,
                task_path="/",
                result=optimization_result,
                status="SUCCESS",
                agent_id=None
            )

        except Exception as e:
            logger.error(f"Failed to finalize optimization: {e}")
            # 创建失败的 TaskCompletedMessage
            result_msg = TaskCompletedMessage(
                message_type=MessageType.TASK_COMPLETED,
                source=str(self.myAddress),
                destination=str(self.reply_to),
                task_id=self.spec.task_id,
                trace_id=self.spec.task_id,
                task_path="/",
                result=None,
                status="FAILED",
                agent_id=None
            )

        # 发送结果并退出
        self.send(self.reply_to, result_msg)
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
