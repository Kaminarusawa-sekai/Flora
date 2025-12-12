import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from thespian.actors import ActorAddress
import uuid

from common.messages.interact_messages import TaskResultMessage
from common.types.task import Task, TaskType
from common.types.task_operation import TaskOperationType, TaskOperationCategory
from capability_actors.loop_scheduler_actor import LoopSchedulerActor
from events.event_bus import event_bus
from events.event_types import EventType

logger = logging.getLogger(__name__)


class AgentActorExtensions:
    """
    AgentActor的扩展类，包含与核心任务创建和恢复无关的功能
    """
    
    def _handle_execution_control_extended(self, operation_type, operation_result: Dict[str, Any],
                                      task: Dict[str, Any], sender: ActorAddress):
        """处理执行控制类操作的扩展部分"""
        task_id = task.get("task_id")

        if operation_type == TaskOperationType.PAUSE_TASK:
            # 暂停任务
            self.log.info(f"Pausing task {task_id}")
            from common.messages.interact_messages import TaskPausedMessage
            pause_msg = TaskPausedMessage(
                task_id=task_id,
                missing_params=[],
                question="任务已暂停"
            )
            self.send(sender, pause_msg)
            # 发布任务暂停事件
            self._report_event(EventType.TASK_PAUSED, task_id, {
                "operation_result": operation_result,
                "message": "任务已暂停"
            })

        elif operation_type == TaskOperationType.CANCEL_TASK:
            # 取消任务
            self._handle_cancel_any_task(task, sender)
            # 发布任务取消事件
            self._report_event(EventType.TASK_CANCELLED, task_id, {
                "operation_result": operation_result,
                "message": "任务已取消"
            })

        elif operation_type == TaskOperationType.RETRY_TASK:
            # 重试任务
            self._handle_re_run_task(task, sender)
            # 发布任务重试事件，这里会触发新的任务创建

        else:
            task_result = TaskResultMessage(
                task_id=task_id,
                result=None,
                error=f"Unsupported execution control operation: {operation_type.value}",
                message=None
            )
            self.send(sender, task_result)
    
    def _handle_task_modification(self, operation_type, operation_result: Dict[str, Any],
                                  task: Dict[str, Any], sender: ActorAddress):
        """处理任务修改类操作"""
        task_id = task.get("task_id")

        if operation_type == TaskOperationType.COMMENT_ON_TASK:
            comment = operation_result.get("parameters", {}).get("comment", "")
            self._handle_add_comment(task, comment, sender)
            # 发布评论添加事件
            self._report_event(EventType.COMMENT_ADDED, task_id, {
                "comment": comment,
                "operation_result": operation_result
            })

        elif operation_type == TaskOperationType.REVISE_RESULT:
            revision = operation_result.get("parameters", {}).get("revision", "")
            self._handle_revise_result(task, revision, sender)
            # 发布任务更新事件
            self._report_event(EventType.TASK_UPDATED, task_id, {
                "revision": revision,
                "operation_result": operation_result
            })

        else:
            task_result = TaskResultMessage(
                task_id=task_id,
                result=None,
                error=f"Unsupported modification operation: {operation_type.value}",
                message=None
            )
            self.send(sender, task_result)
    
    def _handle_task_query(self, operation_type, operation_result: Dict[str, Any],
                          task: Dict[str, Any], sender: ActorAddress):
        """处理任务查询类操作"""
        task_id = task.get("task_id")

        # TODO: 实现查询逻辑
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "message_type": "query_result",
                "result": f"Query operation {operation_type.value} not fully implemented yet"
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _handle_new_task(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str, parent_task_id: str):
        """处理新增任务"""
        # 调用新的_handle_new_task_execution方法
        self._handle_task_creation(task, sender)
    
    def _handle_query_operation(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str):
        """处理查询相关操作"""
        # 这里实现查询相关的逻辑
        task_id = task.get("task_id", "")
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "status": "query_result",
                "message": f"查询结果：{current_desc}"
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _handle_chat_operation(self, task: Dict[str, Any], sender: ActorAddress, current_desc: str):
        """处理闲聊相关操作"""
        # 这里实现闲聊相关的逻辑
        task_id = task.get("task_id", "")
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "status": "chat_response",
                "message": f"闲聊回复：{current_desc}"
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _handle_loop_task_setup(self, task: Dict[str, Any], sender: ActorAddress):
        """处理循环任务设置"""
        # 调用现有的add_loop_task方法
        self.add_loop_task(task, sender)
    
    def add_loop_task(self, task: Dict[str, Any], sender: ActorAddress):
        """
        注意：Thespian Actor 是事件驱动的，不能阻塞。
        所以我们不在此启动 pika 消费者！
        而是让外部系统（或另一个 Actor）将 RabbitMQ 消息桥接到 Thespian。
        """
        parent_task_id = task.get("task_id")
        if not parent_task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
            
        current_desc = task.get("description") or task.get("content", "")
        self.log.info(f"Registering LOOP task: {parent_task_id}")
        
        # 构造循环执行的消息（当调度器触发时，会发回给自己）
        loop_execution_msg = {
            "message_type": "execute_loop_task",
            "original_task": task,
            "decision": {"is_loop": True}
        }

        # 向全局调度器注册
        loop_interval = self._estimate_loop_interval(current_desc)
        register_msg = {
            "type": "register_loop_task",
            "task_id": parent_task_id,
            "interval_sec": loop_interval,
            "message": loop_execution_msg
        }

        # 获取全局调度器地址（通过 globalName）
        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, register_msg)

        # 保存循环任务到注册表
        loop_task = Task(
            task_id=parent_task_id,
            description=current_desc,
            task_type=TaskType.LOOP,
            user_id=self.current_user_id,
            schedule=str(loop_interval),
            next_run_time=datetime.now().fromtimestamp(time.time() + loop_interval),
            original_input=current_desc
        )
        # 使用任务规划能力保存任务
        try:
            self.task_planner.task_repo.create_task(loop_task)
        except Exception as e:
            self.log.warning(f"Failed to save loop task: {e}")

        # 回复用户：已注册循环任务
        task_result = TaskResultMessage(
            task_id=parent_task_id,
            result={
                "status": "loop_registered",
                "interval_sec": loop_interval,
                "reasoning": "循环任务已成功注册"
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
        return
    
    def _estimate_loop_interval(self, task_desc: str) -> int:
        """
        估算循环任务的执行间隔
        """
        # 这里可以使用LLM来估算，暂时返回默认值
        return 3600  # 默认1小时
    
    def _resolve_task_id_by_reference(self, reference: str) -> Optional[str]:
        """根据用户描述（如“日报”）匹配已注册的循环任务ID"""
        # 使用task_registry根据引用查找任务
        task = self.task_registry.find_task_by_reference(self.current_user_id, reference)
        return task.task_id if task else None
    
    def _handle_trigger_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关循环任务",
                message=None
            )
            self.send(sender, task_result)
            return

        # 向 LoopScheduler 发送“立即执行”消息（自定义类型）
        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "trigger_task_now",
            "task_id": task_id
        })
        task_result = TaskResultMessage(
            task_id=task_id,
            result={"status": "triggered"},
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _handle_cancel_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关循环任务",
                message=None
            )
            self.send(sender, task_result)
            return

        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "cancel_loop_task",
            "task_id": task_id
        })
        task_result = TaskResultMessage(
            task_id=task_id,
            result={"status": "cancelled"},
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _handle_modify_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        ref = intent["task_reference"]
        new_interval = intent.get("new_interval_sec")
        if not new_interval or new_interval <= 0:
            # 让 LLM 估算
            new_interval = self._estimate_loop_interval(intent.get("reasoning", ref))

        task_id = self._resolve_task_id_by_reference(ref)
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关循环任务",
                message=None
            )
            self.send(sender, task_result)
            return

        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(loop_scheduler, {
            "type": "update_loop_interval",
            "task_id": task_id,
            "interval_sec": int(new_interval)
        })
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "status": "updated",
                "new_interval_sec": new_interval
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _handle_pause_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        task_id = self._resolve_task_id_by_reference(intent["task_reference"])
        if task_id:
            self._send_to_scheduler({"type": "pause_loop_task", "task_id": task_id}, sender)
        else:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="任务未找到",
                message=None
            )
            self.send(sender, task_result)
    
    def _handle_resume_existing(self, intent: Dict[str, Any], sender: ActorAddress):
        task_id = self._resolve_task_id_by_reference(intent["task_reference"])
        if task_id:
            self._send_to_scheduler({"type": "resume_loop_task", "task_id": task_id}, sender)
        else:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="任务未找到",
                message=None
            )
            self.send(sender, task_result)
    
    def _handle_add_comment(self, task: dict, comment: str, sender: ActorAddress):
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
        
        # 使用task_registry添加评论
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关任务",
                message=None
            )
            self.send(sender, task_result)
            return
        
        # 添加评论
        comment_obj = {"content": comment, "created_at": datetime.now().isoformat()}
        target_task.comments.append(comment_obj)
        self.task_registry.update_task(task_id, {"comments": target_task.comments})
        task_result = TaskResultMessage(
            task_id=task_id,
            result={"status": "comment_added"},
            error=None,
            message=None
        )
        self.send(sender, task_result)
        
        # 发布评论添加事件
        self._report_event(EventType.COMMENT_ADDED, task_id, {
            "comment": comment_obj,
            "task_status": target_task.status
        })
    
    def _handle_revise_result(self, task: dict, new_content: str, sender: ActorAddress):
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
        
        # 使用task_registry修改结果
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关任务",
                message=None
            )
            self.send(sender, task_result)
            return
        
        # 简单策略：全量替换；高级策略：结构化 patch
        self.task_registry.update_task(task_id, {"corrected_result": new_content})
        task_result = TaskResultMessage(
            task_id=task_id,
            result={"status": "result_revised"},
            error=None,
            message=None
        )
        self.send(sender, task_result)
        
        # 发布任务更新事件
        self._report_event(EventType.TASK_UPDATED, task_id, {
            "action": "revise_result",
            "new_content": new_content,
            "message": "任务结果已修改"
        })
    
    def _handle_re_run_task(self, task: dict, sender: ActorAddress):
        # 重新提交原任务描述
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
        
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关任务",
                message=None
            )
            self.send(sender, task_result)
            return
        
        new_task_msg = {
            "task_id": f"{task_id}_retry_{int(time.time())}",
            "description": target_task.description,
            "original_task_id": task_id,  # 用于追踪
            "user_id": self.current_user_id
        }
        
        # 发布任务重试事件
        self._report_event(EventType.TASK_UPDATED, task_id, {
            "action": "retry",
            "new_task_id": new_task_msg["task_id"],
            "message": "任务正在重试"
        })
        
        # 使用_handle_new_task重新执行任务
        self._handle_new_task(new_task_msg, sender, target_task.description, new_task_msg["task_id"])
    
    def _handle_cancel_any_task(self, task: dict, sender: ActorAddress):
        task_id = task.get("task_id") or task.get("target_task_id")
        if not task_id:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="缺少任务ID",
                message=None
            )
            self.send(sender, task_result)
            return
        
        target_task = self.task_registry.get_task(task_id)
        if not target_task:
            task_result = TaskResultMessage(
                task_id="",
                result=None,
                error="未找到相关任务",
                message=None
            )
            self.send(sender, task_result)
            return
        
        if target_task.type == TaskType.LOOP:
            self._forward_to_loop_scheduler({"type": "cancel_loop_task", "task_id": task_id}, sender)
            # 发布循环任务取消事件
            self._report_event(EventType.TASK_CANCELLED, task_id, {
                "task_type": "loop",
                "message": "循环任务已取消"
            })
        else:
            # 普通任务：标记为 cancelled（若还在运行，可发取消信号）
            self.task_registry.update_task(task_id, {"status": "cancelled"})
            task_result = TaskResultMessage(
                task_id=task_id,
                result={"status": "task_cancelled"},
                error=None,
                message=None
            )
            self.send(sender, task_result)
            # 发布任务取消事件
            self._report_event(EventType.TASK_CANCELLED, task_id, {
                "task_type": "normal",
                "message": "普通任务已取消"
            })
    
    def _forward_to_loop_scheduler(self, intent: Dict[str, Any], task_id: str, sender: ActorAddress):
        """转发给循环调度器"""
        # 获取全局调度器地址（通过 globalName）
        loop_scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        
        # 构造转发消息
        forward_msg = {
            "type": intent.get("type", "trigger_task_now"),
            "task_id": task_id
        }
        
        # 添加额外参数
        if intent.get("type") == "update_loop_interval":
            forward_msg["interval_sec"] = intent.get("new_interval_sec", 3600)
        
        self.send(loop_scheduler, forward_msg)
        task_result = TaskResultMessage(
            task_id=task_id,
            result={
                "status": "command_sent",
                "command": forward_msg["type"]
            },
            error=None,
            message=None
        )
        self.send(sender, task_result)
    
    def _send_to_scheduler(self, msg: dict, reply_to: ActorAddress):
        scheduler = self.createActor(LoopSchedulerActor, globalName="loop_scheduler")
        self.send(scheduler, msg)
        # 可选：等待响应或直接回复
        task_result = TaskResultMessage(
            task_id=msg.get("task_id", ""),
            result={
                "status": "command_sent",
                "command": msg.get("type", "")
            },
            error=None,
            message=None
        )
        self.send(reply_to, task_result)
    
    def _send_optimization_feedback(self, task_id: str, result_msg: Any, success: bool):
        """
        发送优化反馈给OptimizerActor

        仅当任务是循环任务且启用优化时发送
        """
        try:
            # 检查是否是循环任务（可以从task_id或任务注册表查询）
            # 这里简化处理：假设所有loop相关的任务都发送反馈
            # 实际实现中应该查询任务类型

            # 构建执行记录
            import time
            from datetime import datetime

            # 处理不同类型的result_msg
            if hasattr(result_msg, "result"):
                result_data = result_msg.result
                parameters = getattr(result_msg, "parameters", {})
            else:
                result_data = result_msg.get("result", {})
                parameters = result_msg.get("parameters", {})

            execution_record = {
                "execution_time": datetime.now().isoformat(),
                "parameters": parameters,
                "result": result_data,
                "success": success,
                "duration": result_data.get("duration", 0.0) if isinstance(result_data, dict) else 0.0,
                "score": self._calculate_execution_score(result_data, success),
                "error": result_data.get("error") if isinstance(result_data, dict) and not success else None
            }

            # 发送给OptimizerActor
            from capability_actors.optimizer_actor import OptimizerActor

            optimizer = self.createActor(OptimizerActor, globalName="optimizer_actor")

            self.send(optimizer, {
                "type": "execution_feedback",
                "task_id": task_id,
                "execution_record": execution_record
            })

            self.log.debug(f"Sent optimization feedback for task {task_id}")

        except Exception as e:
            # 优化反馈失败不应该影响主流程
            self.log.warning(f"Failed to send optimization feedback for task {task_id}: {e}")
    
    def _calculate_execution_score(self, result_data: Any, success: bool) -> float:
        """
        计算执行分数
        
        Args:
            result_data: 执行结果数据
            success: 是否成功

        Returns:
            0.0-1.0之间的分数
        """

        ##TODO：使用LLM
        if not success:
            return 0.0

        # 基础分数
        base_score = 0.7

        # 根据执行时间调整
        duration = 0.0
        if isinstance(result_data, dict):
            duration = result_data.get("duration", 0.0)
        
        if duration < 1.0:
            base_score += 0.2
        elif duration > 10.0:
            base_score -= 0.2

        # 根据结果质量调整（如果有）
        quality_score = None
        if isinstance(result_data, dict):
            quality_score = result_data.get("quality_score")
        
        if quality_score is not None:
            base_score = (base_score + quality_score) / 2

        # 确保在0-1范围内
        return max(0.0, min(1.0, base_score))
    
    def _dispatch_subtasks(
        self,
        plan: List[Dict[str, Any]],
        parent_task_id: str,
        original_desc: str,
        needs_vault: bool
    ) -> Set[str]:
        """
        ⑦ 任务分发 - 直接发给 TaskGroupAggregatorActor 进行批量管理
        """
        pending = set()

        # 创建 TaskGroupAggregatorActor
        from capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor
        from common.messages.task_messages import TaskGroupRequest, TaskSpec

        task_group_addr = self.createActor(TaskGroupAggregatorActor)

        # 构建任务规范列表
        task_specs = []
        for i, step in enumerate(plan):
            child_cap = step["node_id"]
            child_task_id = f"{parent_task_id}.child_{i}"
            child_desc = step.get("description", "")

            child_memory_ctx = self.memory_cap.build_execution_context(
                task_description=child_desc,
                include_sensitive=needs_vault
            )

            final_child_context = {
                "memory_context": child_memory_ctx,
                "instructions": step.get("intent_params", {}),
                "original_task": original_desc,
                "capability": child_cap
            }

            # 创建任务规范
            task_spec = TaskSpec(
                task_id=child_task_id,
                type=child_cap,  # 能力类型
                parameters=final_child_context,
                repeat_count=1,
                aggregation_strategy="single"
            )
            task_specs.append(task_spec)
            pending.add(child_task_id)

            self._report_event("subtask_spawned", child_task_id, {
                "parent_task_id": parent_task_id,
                "capability": child_cap
            })

        # 创建任务组请求
        group_request = TaskGroupRequest(
            source=self.myAddress,
            destination=task_group_addr,
            group_id=parent_task_id,
            tasks=task_specs,
            reply_to=self.myAddress
        )

        # 发送任务组到 TaskGroupAggregatorActor
        self.send(task_group_addr, group_request)

        return pending
    
    def _report_event(self, event_type: str, task_id: str, data: Dict[str, Any]):
        """报告事件到事件总线"""
        try:
            # 从 self 中获取 agent_id，如果没有则使用默认值
            agent_id = getattr(self, 'agent_id', 'unknown_agent')
            
            # 发布任务事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=event_type,
                source='AgentActorExtensions',
                agent_id=agent_id,
                data=data
            )
        except Exception as e:
            self.log.error(f"Failed to report event {event_type} for task {task_id}: {str(e)}", exc_info=True)
    
    def _should_optimize(self) -> bool:
        """判断是否需要优化"""
        # 简单实现：默认不需要优化
        ## TODO: 待实现
        return True
