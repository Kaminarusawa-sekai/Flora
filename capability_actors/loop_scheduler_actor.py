# loop_scheduler_actor.py
import logging
from thespian.actors import Actor, ActorAddress
import time
import json
from typing import Any, Dict
from datetime import datetime

# 导入任务相关模块
from common.tasks.task import Task
from common.tasks.task_registry import TaskRegistry
from common.tasks.task_type import TaskType
from events.event_bus import event_bus
from events.event_types import EventType

# 定义LoopTask类
class LoopTask:
    def __init__(self, task_id: str, target_actor_address: str, message: Dict, interval_sec: int, next_run_at: float):
        self.task_id = task_id
        self.target_actor_address = target_actor_address
        self.message = message
        self.interval_sec = interval_sec
        self.next_run_at = next_run_at

class LoopSchedulerActor(Actor):
    def __init__(self):
        super().__init__()
        self.log = logging.getLogger("LoopSchedulerActor")
        # 初始化任务注册表
        self.task_registry = TaskRegistry()
        self._listen_to_trigger_queue()  # 如果需要主动消费

    def _listen_to_trigger_queue(self):
        """
        注意：Thespian Actor 是事件驱动的，不能阻塞。
        所以我们不在此启动 pika 消费者！
        而是让外部系统（或另一个 Actor）将 RabbitMQ 消息桥接到 Thespian。
        """
        pass  # 见下方说明

    def receiveMessage(self, msg: Any, sender: ActorAddress):
        if isinstance(msg, dict):
            msg_type = msg.get("type")
            if msg_type == "register_loop_task":
                self._handle_register(msg, sender)
            elif msg_type == "rabbitmq_trigger":
                # 外部桥接器将 RabbitMQ 消息转为此格式
                self._handle_trigger(msg)
            elif msg_type == "trigger_task_now":
                task_id = msg["task_id"]
                # 从数据库或内存中获取任务
                try:
                    task = self.task_registry.get_task(task_id)
                    if task:
                        # 构造执行消息
                        execution_msg = {
                            "message_type": "execute_loop_task",
                            "original_task": {"description": task.description},
                            "decision": {"is_loop": True}
                        }
                        # 获取目标Actor地址
                        target_addr = self.createActor(None, globalName="agent_actor")
                        self.send(target_addr, execution_msg)
                        self.send(sender, {"status": "triggered_now", "task_id": task_id})
                        
                        # 发送任务触发事件
                        event_bus.publish_task_event(
                            task_id=task_id,
                            event_type=EventType.TASK_TRIGGERED.value,
                            source="LoopSchedulerActor",
                            agent_id="loop_scheduler",
                            data={"trigger_type": "manual"}
                        )
                    else:
                        self.send(sender, {"status": "error", "reason": "Task not found"})
                except Exception as e:
                    self.log.error(f"Error triggering task {task_id}: {e}")
                    self.send(sender, {"status": "error", "reason": str(e)})
            elif msg_type == "update_loop_interval":
                task_id = msg["task_id"]
                try:
                    task = self.task_registry.get_task(task_id)
                    if task:
                        task.schedule = str(msg["interval_sec"])
                        self.task_registry.update_task(task_id, {"schedule": task.schedule})
                        self.send(sender, {"status": "interval_updated", "task_id": task_id})
                        
                        # 发送任务更新事件
                        event_bus.publish_task_event(
                            task_id=task_id,
                            event_type=EventType.TASK_UPDATED.value,
                            source="LoopSchedulerActor",
                            agent_id="loop_scheduler",
                            data={"interval_sec": msg["interval_sec"]}
                        )
                    else:
                        self.send(sender, {"status": "error", "reason": "Task not found"})
                except Exception as e:
                    self.log.error(f"Error updating task interval {task_id}: {e}")
                    self.send(sender, {"status": "error", "reason": str(e)})
            elif msg_type == "pause_loop_task":
                task_id = msg["task_id"]
                try:
                    task = self.task_registry.get_task(task_id)
                    if task:
                        # 暂停逻辑
                        self.task_registry.update_task(task_id, {"status": "paused"})
                        self.send(sender, {"status": "paused", "task_id": task_id})
                        
                        # 发送任务暂停事件
                        event_bus.publish_task_event(
                            task_id=task_id,
                            event_type=EventType.TASK_PAUSED.value,
                            source="LoopSchedulerActor",
                            agent_id="loop_scheduler",
                            data={}
                        )
                    else:
                        self.send(sender, {"status": "error", "reason": "Task not found"})
                except Exception as e:
                    self.log.error(f"Error pausing task {task_id}: {e}")
                    self.send(sender, {"status": "error", "reason": str(e)})
            elif msg_type == "resume_loop_task":
                task_id = msg["task_id"]
                try:
                    task = self.task_registry.get_task(task_id)
                    if task:
                        # 恢复逻辑
                        self.task_registry.update_task(task_id, {"status": "running"})
                        self.send(sender, {"status": "resumed", "task_id": task_id})
                        
                        # 发送任务恢复事件
                        event_bus.publish_task_event(
                            task_id=task_id,
                            event_type=EventType.TASK_RESUMED.value,
                            source="LoopSchedulerActor",
                            agent_id="loop_scheduler",
                            data={}
                        )
                    else:
                        self.send(sender, {"status": "error", "reason": "Task not found"})
                except Exception as e:
                    self.log.error(f"Error resuming task {task_id}: {e}")
                    self.send(sender, {"status": "error", "reason": str(e)})
            elif msg_type == "cancel_loop_task":
                task_id = msg["task_id"]
                try:
                    # 删除任务逻辑
                    self.task_registry.delete_task(task_id)
                    self.send(sender, {"status": "cancelled", "task_id": task_id})
                    
                    # 发送任务取消事件
                    event_bus.publish_task_event(
                        task_id=task_id,
                        event_type=EventType.TASK_CANCELLED.value,
                        source="LoopSchedulerActor",
                        agent_id="loop_scheduler",
                        data={}
                    )
                except Exception as e:
                    self.log.error(f"Error cancelling task {task_id}: {e}")
                    self.send(sender, {"status": "error", "reason": str(e)})

    def _handle_register(self, msg: Dict[str, Any], sender: ActorAddress):
        task_id = msg["task_id"]
        interval = msg["interval_sec"]
        message = msg["message"]

        # 构造 LoopTask（地址转为字符串）
        loop_task = LoopTask(
            task_id=task_id,
            target_actor_address=str(sender),
            message=message,
            interval_sec=interval,
            next_run_at=time.time() + interval
        )

        try:
            # 保存任务到注册表
            # 注意：这里我们直接使用Task类，因为TaskRegistry期望的是Task对象
            from common.tasks.task import Task
            from datetime import datetime
            
            task = Task(
                task_id=task_id,
                description=message.get("original_task", {}).get("description", "循环任务"),
                task_type=TaskType.LOOP,
                user_id="system",
                schedule=str(interval),
                next_run_time=datetime.now().fromtimestamp(time.time() + interval),
                original_input=message.get("original_task", {}).get("description", "循环任务")
            )
            
            self.task_registry.create_task(task)
            self.send(sender, {"status": "registered", "task_id": task_id})
            
            # 发送循环任务注册事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.LOOP_TASK_REGISTERED.value,
                source="LoopSchedulerActor",
                agent_id="loop_scheduler",
                data={
                    "interval_sec": interval,
                    "target_actor": str(sender)
                }
            )
        except Exception as e:
            self.log.error(f"Failed to register task: {e}")
            self.send(sender, {"status": "error", "reason": str(e)})

    def _handle_trigger(self, trigger_msg: Dict[str, Any]):
        """处理来自 RabbitMQ 的触发消息"""
        task_id = trigger_msg["task_id"]
        target_addr_str = trigger_msg["target_actor_address"]
        original_message = trigger_msg["message"]
        interval_sec = trigger_msg["interval_sec"]

        # 将字符串地址转回 ActorAddress（需自定义解析，Thespian 无标准方式）
        # 简化：假设你有一个地址注册表，或使用 globalName
        # 此处假设 target 是 globalName
        try:
            target_addr = self.createActor(None, globalName=target_addr_str)
            self.send(target_addr, original_message)
            
            # 发送任务触发事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.TASK_TRIGGERED.value,
                source="LoopSchedulerActor",
                agent_id="loop_scheduler",
                data={"trigger_type": "rabbitmq"}
            )

            # 重新注册下一次执行（实现循环）
            next_task = LoopTask(
                task_id=task_id,
                target_actor_address=target_addr_str,
                message=original_message,
                interval_sec=interval_sec,
                next_run_at=time.time() + interval_sec
            )
            
            # 更新任务的下次运行时间
            self.task_registry.update_task(task_id, {
                "next_run_time": datetime.now().fromtimestamp(time.time() + interval_sec)
            })
        except Exception as e:
            self.log.error(f"Failed to trigger task {task_id}: {e}")