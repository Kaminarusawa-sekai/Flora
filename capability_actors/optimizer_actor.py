"""
OptimizerActor - 优化器Actor
负责循环任务的异步优化和反馈学习

架构说明:
- 执行(Execution)和优化(Optimization)是两个独立的生命周期
- LoopSchedulerActor: 负责"何时做"（Timing）和"存配置"（State）
- AgentActor: 负责"做什么"（Execution）
- OptimizerActor: 负责"怎么做得更好"（Reflection & Tuning）
"""
import logging
from typing import Dict, Any, Optional, List
from thespian.actors import Actor, ActorAddress
from datetime import datetime

# 导入优化能力
from capabilities.optimization import OptimizationInterface, MultiFeatureOptimizer

# 导入事件总线
from events.event_bus import event_bus
from events.event_types import EventType


class OptimizerActor(Actor):
    """
    优化器Actor - 异步反馈优化管理器

    职责:
    1. 管理每个循环任务的优化器实例
    2. 收集执行历史和反馈
    3. 生成优化建议
    4. 更新任务参数
    """

    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("OptimizerActor")

        # 为每个任务维护独立的优化器实例
        # task_id -> MultiFeatureOptimizer
        self.optimizers: Dict[str, OptimizationInterface] = {}

        # 存储每个任务的执行历史
        # task_id -> List[execution_record]
        self.execution_history: Dict[str, List[Dict[str, Any]]] = {}

        # 优化配置
        # task_id -> config
        self.optimization_configs: Dict[str, Dict[str, Any]] = {}

        self.log.info("OptimizerActor initialized")

    def receiveMessage(self, msg: Any, sender: ActorAddress):
        """处理接收到的消息"""
        try:
            if isinstance(msg, dict):
                msg_type = msg.get("type") or msg.get("message_type")

                handlers = {
                    "register_optimization": self._handle_register_optimization,
                    "execution_feedback": self._handle_execution_feedback,
                    "request_optimization": self._handle_request_optimization,
                    "get_optimization_stats": self._handle_get_stats,
                    "reset_optimizer": self._handle_reset_optimizer,
                    "unregister_optimization": self._handle_unregister_optimization,
                }

                handler = handlers.get(msg_type)
                if handler:
                    handler(msg, sender)
                else:
                    self.log.warning(f"Unknown message type: {msg_type}")
        except Exception as e:
            self.log.exception(f"Error in OptimizerActor: {e}")
            self.send(sender, {
                "type": "error",
                "error": str(e)
            })

    def _handle_register_optimization(self, msg: Dict[str, Any], sender: ActorAddress):
        """
        注册需要优化的循环任务

        消息格式:
        {
            "type": "register_optimization",
            "task_id": "task_xxx",
            "config": {
                "default_parameters": {...},
                "knowledge_base_path": "path/to/kb",
                "optimization_interval": 10  # 每执行10次优化一次
            }
        }
        """
        task_id = msg.get("task_id")
        config = msg.get("config", {})

        if not task_id:
            self.log.error("Missing task_id in register_optimization")
            self.send(sender, {
                "type": "registration_failed",
                "error": "Missing task_id"
            })
            return

        try:
            # 创建优化器实例
            optimizer = MultiFeatureOptimizer(config=config)
            self.optimizers[task_id] = optimizer
            self.optimization_configs[task_id] = config
            self.execution_history[task_id] = []

            self.log.info(f"Registered optimization for task {task_id}")

            # 发布优化注册事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.OPTIMIZATION_REGISTERED.value,
                source="OptimizerActor",
                agent_id="optimizer",
                data={"config": config}
            )

            self.send(sender, {
                "type": "registration_success",
                "task_id": task_id
            })

        except Exception as e:
            self.log.error(f"Failed to register optimization for task {task_id}: {e}")
            self.send(sender, {
                "type": "registration_failed",
                "task_id": task_id,
                "error": str(e)
            })

    def _handle_execution_feedback(self, msg: Dict[str, Any], sender: ActorAddress):
        """
        处理任务执行反馈

        消息格式:
        {
            "type": "execution_feedback",
            "task_id": "task_xxx",
            "execution_record": {
                "execution_time": "2025-11-29T10:00:00",
                "parameters": {...},
                "result": {...},
                "success": True,
                "duration": 1.5,
                "score": 0.85,
                "error": None
            }
        }
        """
        task_id = msg.get("task_id")
        execution_record = msg.get("execution_record", {})

        if not task_id or task_id not in self.optimizers:
            self.log.warning(f"Received feedback for unregistered task {task_id}")
            return

        try:
            # 添加到执行历史
            if task_id not in self.execution_history:
                self.execution_history[task_id] = []

            self.execution_history[task_id].append(execution_record)

            # 让优化器学习
            optimizer = self.optimizers[task_id]
            learning_success = optimizer.learn_from_result(
                task_id=task_id,
                result=execution_record,
                feedback=msg.get("feedback")
            )

            self.log.info(f"Learning from execution for task {task_id}: success={learning_success}")

            # 检查是否需要触发优化
            config = self.optimization_configs.get(task_id, {})
            optimization_interval = config.get("optimization_interval", 10)

            if len(self.execution_history[task_id]) % optimization_interval == 0:
                # 触发优化
                self._trigger_optimization(task_id, sender)

            # 发布学习事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.OPTIMIZATION_LEARNED.value,
                source="OptimizerActor",
                agent_id="optimizer",
                data={
                    "learning_success": learning_success,
                    "history_count": len(self.execution_history[task_id])
                }
            )

        except Exception as e:
            self.log.error(f"Failed to process feedback for task {task_id}: {e}")

    def _trigger_optimization(self, task_id: str, original_sender: ActorAddress):
        """触发优化并发送更新给LoopSchedulerActor"""
        try:
            optimizer = self.optimizers.get(task_id)
            if not optimizer:
                return

            # 获取优化后的参数
            best_params = optimizer.get_best_parameters()

            if not best_params:
                self.log.info(f"No optimized parameters available for task {task_id}")
                return

            # 获取统计信息
            stats = optimizer.get_optimization_stats()

            self.log.info(f"Triggering optimization for task {task_id}, best_score: {stats.get('best_score')}")

            # 发送优化结果给LoopSchedulerActor
            from capability_actors.loop_scheduler_actor import LoopSchedulerActor
            loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")

            self.send(loop_scheduler, {
                "type": "apply_optimization",
                "task_id": task_id,
                "optimized_parameters": best_params,
                "optimization_stats": stats
            })

            # 发布优化触发事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.OPTIMIZATION_TRIGGERED.value,
                source="OptimizerActor",
                agent_id="optimizer",
                data={
                    "best_parameters": best_params,
                    "stats": stats
                }
            )

        except Exception as e:
            self.log.error(f"Failed to trigger optimization for task {task_id}: {e}")

    def _handle_request_optimization(self, msg: Dict[str, Any], sender: ActorAddress):
        """
        手动请求优化

        消息格式:
        {
            "type": "request_optimization",
            "task_id": "task_xxx"
        }
        """
        task_id = msg.get("task_id")

        if not task_id or task_id not in self.optimizers:
            self.send(sender, {
                "type": "optimization_failed",
                "error": f"Task {task_id} not registered for optimization"
            })
            return

        try:
            optimizer = self.optimizers[task_id]
            history = self.execution_history.get(task_id, [])

            # 如果没有足够的历史数据，返回错误
            if len(history) < 3:
                self.send(sender, {
                    "type": "optimization_failed",
                    "error": "Not enough execution history for optimization",
                    "history_count": len(history)
                })
                return

            # 执行优化
            task_info = {
                "task_id": task_id,
                "task_name": task_id,  # 可以从任务注册表获取更详细的信息
                "current_state": {},
                "constraints": self.optimization_configs.get(task_id, {}).get("constraints", {})
            }

            optimized_params = optimizer.optimize_task(task_info, history)
            stats = optimizer.get_optimization_stats()

            self.send(sender, {
                "type": "optimization_result",
                "task_id": task_id,
                "optimized_parameters": optimized_params,
                "stats": stats
            })

            # 同时发送给LoopSchedulerActor
            from capability_actors.loop_scheduler_actor import LoopSchedulerActor
            loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")

            self.send(loop_scheduler, {
                "type": "apply_optimization",
                "task_id": task_id,
                "optimized_parameters": optimized_params,
                "optimization_stats": stats
            })

        except Exception as e:
            self.log.error(f"Failed to optimize task {task_id}: {e}")
            self.send(sender, {
                "type": "optimization_failed",
                "task_id": task_id,
                "error": str(e)
            })

    def _handle_get_stats(self, msg: Dict[str, Any], sender: ActorAddress):
        """获取优化统计信息"""
        task_id = msg.get("task_id")

        if task_id:
            # 获取特定任务的统计
            if task_id in self.optimizers:
                stats = self.optimizers[task_id].get_optimization_stats()
                stats["execution_count"] = len(self.execution_history.get(task_id, []))

                self.send(sender, {
                    "type": "optimization_stats",
                    "task_id": task_id,
                    "stats": stats
                })
            else:
                self.send(sender, {
                    "type": "error",
                    "error": f"Task {task_id} not registered"
                })
        else:
            # 获取所有任务的统计
            all_stats = {}
            for tid, optimizer in self.optimizers.items():
                stats = optimizer.get_optimization_stats()
                stats["execution_count"] = len(self.execution_history.get(tid, []))
                all_stats[tid] = stats

            self.send(sender, {
                "type": "all_optimization_stats",
                "stats": all_stats
            })

    def _handle_reset_optimizer(self, msg: Dict[str, Any], sender: ActorAddress):
        """重置优化器"""
        task_id = msg.get("task_id")

        if not task_id or task_id not in self.optimizers:
            self.send(sender, {
                "type": "reset_failed",
                "error": f"Task {task_id} not registered"
            })
            return

        try:
            optimizer = self.optimizers[task_id]
            success = optimizer.reset()

            # 清空执行历史
            self.execution_history[task_id] = []

            self.log.info(f"Reset optimizer for task {task_id}")

            self.send(sender, {
                "type": "reset_success",
                "task_id": task_id
            })

            # 发布重置事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.OPTIMIZATION_RESET.value,
                source="OptimizerActor",
                agent_id="optimizer",
                data={}
            )

        except Exception as e:
            self.log.error(f"Failed to reset optimizer for task {task_id}: {e}")
            self.send(sender, {
                "type": "reset_failed",
                "task_id": task_id,
                "error": str(e)
            })

    def _handle_unregister_optimization(self, msg: Dict[str, Any], sender: ActorAddress):
        """取消注册优化"""
        task_id = msg.get("task_id")

        if not task_id:
            return

        try:
            # 保存优化器状态（可选）
            if task_id in self.optimizers:
                optimizer = self.optimizers[task_id]
                state = optimizer.save_state()
                # 这里可以将state保存到持久化存储

                # 移除优化器
                del self.optimizers[task_id]
                del self.execution_history[task_id]
                del self.optimization_configs[task_id]

                self.log.info(f"Unregistered optimization for task {task_id}")

                self.send(sender, {
                    "type": "unregistration_success",
                    "task_id": task_id
                })

                # 发布取消注册事件
                event_bus.publish_task_event(
                    task_id=task_id,
                    event_type=EventType.OPTIMIZATION_UNREGISTERED.value,
                    source="OptimizerActor",
                    agent_id="optimizer",
                    data={}
                )
        except Exception as e:
            self.log.error(f"Failed to unregister optimization for task {task_id}: {e}")
