import logging
from typing import Dict, Any, Optional
from thespian.actors import ActorAddress, Actor, ActorExitRequest,ChildActorExited
from ..common.messages.task_messages import ExecuteTaskMessage, ExecutionResultMessage, TaskCompletedMessage, AgentTaskMessage
from ..capabilities import get_capability
from ..capabilities.llm_memory.interface import IMemoryCapability
from ..events.event_bus import event_bus
from common.event.event_type import EventType

logger = logging.getLogger(__name__)

class LeafActor(Actor):
    def __init__(self):
        super().__init__()
        self.agent_id: str = ""
        self.memory_cap: Optional[IMemoryCapability] = None
        self.meta = None
        self.log = logging.getLogger("LeafActor")
        self.current_user_id: Optional[str] = None
        self.task_id_to_sender: Dict[str, ActorAddress] = {}

    def receiveMessage(self, message: Any, sender: ActorAddress):
        if isinstance(message, ActorExitRequest):
            # 可选：做清理工作
            logger.info("Received ActorExitRequest, shutting down.")
            return  # Thespian will destroy the actor automatically
        elif isinstance(message, ChildActorExited):
            # 可选：处理子 Actor 退出
            logger.info(f"Child actor exited: {message.childAddress}, reason: {message.__dict__}")
            return
        try:
            if isinstance(message, AgentTaskMessage):
                self._handle_task(message, sender)
            elif isinstance(message, ExecutionResultMessage):
                # 处理执行结果消息类型
                self._handle_execution_result(message, sender)
            else:
                self.log.warning(f"Unknown message type: {type(message)}")
        except Exception as e:
            self.log.exception(f"Error in LeafActor {self.agent_id}: {e}")

    def _handle_init(self, msg: Dict[str, Any], sender: ActorAddress):
        self.agent_id = msg["agent_id"]
        from .tree.tree_manager import TreeManager
        tree_manager = TreeManager()
        self.meta = tree_manager.get_agent_meta(self.agent_id)
        try:
            self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
            self.log = logging.getLogger(f"LeafActor_{self.agent_id}")
            self.log.info(f"LeafActor initialized for {self.agent_id}")
            self.send(sender, {"status": "initialized", "agent_id": self.agent_id})
        except Exception as e:
            self.log.error(f"Failed to initialize capabilities for agent {self.agent_id}: {e}")
            self.send(sender, {"status": "init_failed", "agent_id": self.agent_id, "error": str(e)})
            return

    def _handle_task(self, task: AgentTaskMessage, sender: ActorAddress):
        """
        处理叶子节点任务执行
        """
        # 如果尚未初始化，则执行初始化逻辑
        if not self.agent_id:
            self.agent_id = task.agent_id
            from .tree.tree_manager import TreeManager
            tree_manager = TreeManager()
            self.meta = tree_manager.get_agent_meta(self.agent_id)
            try:
                self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
                self.log = logging.getLogger(f"LeafActor_{self.agent_id}")
                self.log.info(f"LeafActor initialized for {self.agent_id}")
            except Exception as e:
                self.log.error(f"Failed to initialize capabilities for agent {self.agent_id}: {e}")
                return
        
        if not self._ensure_memory_ready():
            return

        # 保存原始任务规格，用于断点续传
        self.original_spec = task

        # 获取任务信息
        user_input = task.get_user_input()
        user_id = task.user_id
        parent_task_id = task.task_id
        reply_to = task.reply_to or sender

        if not parent_task_id:
            self.log.error("Missing task_id in agent_task")
            return

        self.task_id_to_sender[parent_task_id] = reply_to
        self.current_user_id = user_id

        self.log.info(f"[LeafActor] Handling task {parent_task_id}: {user_input[:50]}...")

        if self.meta is None:
            # 构建错误响应：meta 不存在，无法执行任务
            error_msg = TaskCompletedMessage(
                task_id=parent_task_id,
                trace_id=task.trace_id,
                task_path=task.task_path,
                result=None,
                status="ERROR",
                agent_id=self.agent_id
            )
            self.send(reply_to, error_msg)
            
            # 发布任务错误事件
            event_bus.publish_task_event(
                task_id=parent_task_id,
                event_type=EventType.TASK_FAILED.value,
                trace_id=task.trace_id,
                task_path=task.task_path,
                source="LeafActor",
                agent_id=self.agent_id,
                user_id=self.current_user_id,
                data={"error": "Agent meta not found", "status": "ERROR"}
            )
            
            # 清理任务映射（避免残留）
            self.task_id_to_sender.pop(parent_task_id, None)
            return
        else:# 执行叶子节点逻辑
            self._execute_leaf_logic(task, reply_to)

    def _execute_leaf_logic(self, task: AgentTaskMessage, sender: ActorAddress):
        """处理叶子节点执行逻辑"""
        # 获取 ExecutionActor
        from ..capability_actors.execution_actor import ExecutionActor
        exec_actor = self.createActor(ExecutionActor)

        # 构建 running_config（原 params 内容）
        running_config = {
            "api_key": self.meta["dify"],
            "inputs": task.parameters,
            "agent_id": self.agent_id,
            "user_id": self.current_user_id,
            # 如果执行器仍需要原始内容/描述，可显式传入
            "content": str(task.content or ""),
            "description": str(task.description or ""),
            # 注意：task.context 可能已通过 enriched_context 或 global_context 传递，
            # 若仍需在此透传，可加一行：
            # "context": task.context,
        }

        # 构建执行请求消息
        exec_request = ExecuteTaskMessage(
            task_id=task.task_id,
            task_path=task.task_path,
            trace_id=task.trace_id,
            capability="dify",
            running_config=running_config,
            content=task.content,          # 来自 TaskMessage
            description=task.description,  # 来自 TaskMessage
            global_context=task.global_context,
            enriched_context=task.enriched_context,
            user_id=self.current_user_id,
            sender=str(self.myAddress),
            reply_to=self.myAddress
        )

        
        # 发布任务开始事件
        event_bus.publish_task_event(
            task_id=task.task_id,
            event_type=EventType.TASK_CREATED.value,
            trace_id=task.trace_id,
            task_path=task.task_path,
            source="LeafActor",
            agent_id=self.agent_id,
            user_id=self.current_user_id,
            data={"node_id": self.agent_id, "type": "leaf_execution"}
        )
        
        self.send(exec_actor, exec_request)

    def _handle_execution_result(self, result_msg: ExecutionResultMessage, sender: ActorAddress):
        """处理执行结果消息"""
        task_id = result_msg.task_id
        result_data = result_msg.result
        status = result_msg.status
        error = result_msg.error
        missing_params = result_msg.missing_params

        # 构建 TaskCompletedMessage 向上报告
        task_completed_msg = TaskCompletedMessage(
            task_id=task_id,
            trace_id=result_msg.trace_id,
            task_path=result_msg.task_path,
            result=result_data,
            status=status,
            agent_id=self.agent_id
        )

        # 发送结果给原始发送者
        original_sender = self.task_id_to_sender.get(task_id, sender)
        self.send(original_sender, task_completed_msg)

        # 处理断点续传逻辑
        if status == "NEED_INPUT":
            # 1. 发布任务暂停事件
            event_bus.publish_task_event(
                task_id=task_id,
                event_type=EventType.TASK_PAUSED.value,
                trace_id=result_msg.trace_id,
                task_path=result_msg.task_path,
                source="LeafActor",
                agent_id=self.agent_id,
                user_id=self.current_user_id,
                data={"result": result_data, "status": status, "missing_params": missing_params}
            )
            
            # 2. 保存当前上下文，用于断点续传
            self._save_execution_state(task_id)
            
            # 3. 清理映射（等待外部输入后再恢复）
            self.task_id_to_sender.pop(task_id, None)
            return
        
        # 处理成功或失败的情况
        if status == "SUCCESS":
            event_type = EventType.TASK_COMPLETED.value
        else:
            event_type = EventType.TASK_FAILED.value
        
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=event_type,
            trace_id=result_msg.trace_id,
            task_path=result_msg.task_path,
            source="LeafActor",
            agent_id=self.agent_id,
            user_id=self.current_user_id,
            data={"result": result_data, "status": status}
        )

        # 清理映射
        self.task_id_to_sender.pop(task_id, None)

    def _save_execution_state(self, task_id: str) -> None:
        """
        保存执行状态，用于断点续传
        
        Args:
            task_id: 任务ID
        """
        try:
            # 使用内存能力保存状态
            if self.memory_cap:
                # 构建状态数据

                ##TODO：抽象为DTO，然后对接redis
                state_data = {
                    "agent_id": self.agent_id,
                    "original_spec": getattr(self, "original_spec", None),
                    "current_user_id": self.current_user_id,
                    "meta": self.meta,
                    "timestamp": "2025-12-05"
                }
                # 保存到内存
                self.memory_cap.save_state(task_id, state_data)
                self.log.info(f"Saved execution state for task {task_id}")
        except Exception as e:
            self.log.error(f"Failed to save execution state for task {task_id}: {e}")
    
    def _load_execution_state(self, task_id: str) -> Any:
        """
        加载执行状态，用于断点续传
        
        Args:
            task_id: 任务ID
            
        Returns:
            Any: 保存的状态数据
        """
        try:
            if self.memory_cap:
                state_data = self.memory_cap.load_state(task_id)
                if state_data:
                    self.log.info(f"Loaded execution state for task {task_id}")
                    return state_data
        except Exception as e:
            self.log.error(f"Failed to load execution state for task {task_id}: {e}")
        return None
    
    def _handle_user_input(self, msg: Dict[str, Any], sender: ActorAddress) -> None:
        """
        处理用户输入，恢复中断的任务
        
        Args:
            msg: 包含 task_id 和用户输入数据的消息
            sender: 发送者
        """
        task_id = msg.get("task_id")
        user_input_data = msg.get("data", {})
        
        if not task_id:
            self.log.error("Missing task_id in user input message")
            return
        
        # 1. 加载保存的状态
        state_data = self._load_execution_state(task_id)
        if not state_data:
            self.log.error(f"No saved state found for task {task_id}")
            return
        
        # 2. 恢复上下文
        self.original_spec = state_data.get("original_spec")
        self.current_user_id = state_data.get("current_user_id")
        
        # 3. 获取原始任务信息
        from ..capability_actors.execution_actor import ExecutionActor
        exec_actor = self.createActor(ExecutionActor)
        
        # 4. 构建新的执行请求，合并用户输入数据
        new_params = {
            "api_key": self.meta["dify"],
            "inputs": {**(self.original_spec.parameters), **user_input_data},
            "agent_id": self.agent_id,
            "user_id": self.current_user_id,
            "content": str(self.original_spec.description or "") + self.original_spec.content + str(self.original_spec.context or ""),
        }
        
        # 5. 创建执行请求消息
        exec_request = ExecuteTaskMessage(
            task_id=task_id,
            capability="dify",
            params=new_params,
            sender=str(self.myAddress),
            reply_to=str(self.myAddress)
        )
        
        # 6. 重新执行任务
        self.log.info(f"Resuming execution for task {task_id} with user input")
        self.task_id_to_sender[task_id] = sender
        self.send(exec_actor, exec_request)
    
    def _ensure_memory_ready(self) -> bool:
        if self.memory_cap is None:
            self.log.error("Memory capability not ready")
            return False
        return True
