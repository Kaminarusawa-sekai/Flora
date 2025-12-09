# capability_actors/result_aggregator_actor.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from thespian.actors import Actor, ActorExitRequest,ChildActorExited
from common.messages.task_messages import (
    TaskCompletedMessage, ExecuteTaskMessage, TaskSpec, TaskMessage,
    ResultAggregatorTaskRequestMessage
)
from common.messages.agent_messages import AgentTaskMessage
from common.messages.types import MessageType

# 引入 AgentActor


import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ResultAggregatorActor(Actor):
    """
    Result Aggregator Actor - 任务执行与结果聚合器
    
    修改后逻辑：
    1. 接收来自 TaskGroupAggregator 的任务请求
    2. 根据 executor ID 获取或创建对应的 AgentActor
    3. 发送 AgentTaskMessage 给 AgentActor 执行
    4. 负责执行过程中的 重试 (Retry) 和 超时 (Timeout) 管理
    5. 将最终结果返回给上层（TaskGroupAggregator 或 Creator）
    """

    def __init__(self):
        super().__init__()
        self._pending_tasks: Dict[str, Any] = {}
        self._completed_tasks: Dict[str, Any] = {}
        self._failed_tasks: Dict[str, Any] = {}
        self._retries: Dict[str, int] = {}
        self._actor_ref_cache: Dict[str, Any] = {}

        self.registry = None
        self.current_user_id = None
        self._max_retries = 3
        self._timeout = 300
        self._creator: Any = None
        self._aggregation_strategy: str = "sequential"

        # ✅ 上下文字段：只在首次任务请求时设置，之后不再修改
        self._root_task_id: Optional[str] = None
        self._trace_id: Optional[str] = None
        self._base_task_path: Optional[str] = None

    def receiveMessage(self, message: Any, sender: Any) -> None:

        
        """处理接收到的消息"""

        if isinstance(message, ActorExitRequest):
            # 可选：做清理工作
            logger.info("Received ActorExitRequest, shutting down.")
            return  # Thespian will destroy the actor automatically
        elif isinstance(message, ChildActorExited):
            # 可选：处理子 Actor 退出
            logger.info(f"Child actor exited: {message.childAddress}, reason: {message.__dict__}")
            return
        try:
            if isinstance(message, ResultAggregatorTaskRequestMessage):
                # ✅ 只在此处初始化上下文！不要在开头无条件覆盖
                self._handle_result_aggregator_request(message, sender)

            elif isinstance(message, TaskCompletedMessage):
                self._handle_task_completed_message(message, sender)

            else:
                logger.warning(f"Unknown message type: {type(message)}")

        except Exception as e:
            logger.error(f"ResultAggregatorActor execution failed: {e}", exc_info=True)
            self._send_error_to_creator(str(e))

    def _handle_result_aggregator_request(self, msg: ResultAggregatorTaskRequestMessage, sender: Any) -> None:
        """处理基于spec的任务请求，并初始化上下文"""
        # ✅ 初始化上下文（仅一次）
        if self._root_task_id is None:
            self._creator = sender
            self._root_task_id = msg.task_id          # e.g., "step_1"
            self._trace_id = msg.trace_id or f"trace_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            self._base_task_path = msg.task_path      # e.g., "root.step1"

        # 其他配置
        self._max_retries = 3
        self._timeout = 300
        self._aggregation_strategy = "sequential"

        from agents.tree.tree_manager import treeManager
        self.registry = treeManager
        self.current_user_id = msg.user_id

        task_spec = msg.spec
        agent_id = task_spec.executor
        if not agent_id:
            self._process_failure(self._root_task_id, "Missing 'executor' in task spec", sender)
            return

        logger.info(f"ResultAggregator: Received task request for AgentActor: {agent_id}")

        task_id = f"step_{task_spec.step}"
        if task_id not in self._pending_tasks:
            self._pending_tasks[task_id] = {
                "spec": task_spec,
                "executor": agent_id,
                "parameters": task_spec.params
            }
            self._retries[task_id] = 0

        try:
            agent_ref = self._get_or_create_actor_ref(agent_id)

            task_msg = AgentTaskMessage(
                agent_id=agent_id,
                task_id=task_id,
                trace_id=self._trace_id,
                task_path=msg.task_path,
                content=task_spec.params,
                description=task_spec.description,
                user_id=self.current_user_id,
                reply_to=self.myAddress,
                context={},
                is_parameter_completion=False,
                parameters={}
            )

            self.send(agent_ref, task_msg)

        except Exception as e:
            logger.error(f"Failed to spawn agent task {task_id}: {e}", exc_info=True)
            self._process_failure(task_id, str(e), sender)

    def _get_or_create_actor_ref(self, agent_id: str):
        if agent_id not in self._actor_ref_cache:
            if not self.registry:
                raise ValueError("Registry not initialized in ResultAggregator")

            is_leaf = self._is_leaf_node(agent_id)

            if is_leaf:
                from agents.leaf_actor import LeafActor
                ref = self.createActor(LeafActor)
                actor_type = "LeafActor"
            else:
                from agents.agent_actor import AgentActor
                ref = self.createActor(AgentActor)
                actor_type = "AgentActor"

            agent_info = self.registry.get_agent_meta(agent_id)
            capabilities = agent_info.get("capability", []) if agent_info else ["default"]

            self._actor_ref_cache[agent_id] = ref
            logger.info(f"Created new {actor_type} for {agent_id}")

        return self._actor_ref_cache[agent_id]

    def _handle_task_completed_message(self, msg: TaskCompletedMessage, sender: Any) -> None:
        logger.info(f"Received TaskCompletedMessage for {msg.task_id}: {msg.status}")

        if msg.status == "SUCCESS":
            self._process_success(msg.task_id, msg.result)
        elif msg.status == "NEED_INPUT":
            self._handle_need_input(msg, sender)
        else:
            error = f"Task failed with status: {msg.status}"
            self._process_failure(msg.task_id, error, sender)

    def _handle_need_input(self, msg: TaskCompletedMessage, sender: Any) -> None:
        logger.info(f"Task {msg.task_id} needs input, submitting to upper layer")
        # ✅ 这里已正确传递上下文
        self.send(self._creator, TaskCompletedMessage(
            task_id=msg.task_id,
            task_path=msg.task_path,
            trace_id=msg.trace_id,
            message_type=MessageType.TASK_COMPLETED,
            result=msg.result,
            status="NEED_INPUT",
            agent_id=msg.agent_id
        ))
        logger.info(f"Task {msg.task_id} execution blocked, waiting for input")

    def _process_success(self, task_id: str, result: Any) -> None:
        if not task_id:
            return

        self._pending_tasks.pop(task_id, None)
        self._failed_tasks.pop(task_id, None)
        self._completed_tasks[task_id] = result

        self._check_completion()

    def _process_failure(self, task_id: str, error: str, worker_sender: Any) -> None:
        if not task_id:
            return

        current_retry = self._retries.get(task_id, 0)

        if current_retry < self._max_retries:
            self._retries[task_id] = current_retry + 1
            logger.warning(f"Task {task_id} failed. Retrying ({self._retries[task_id]}/{self._max_retries}). Error: {error}")

            task_info = self._pending_tasks.get(task_id)
            if task_info:
                agent_id = task_info.get("executor")
                try:
                    agent_ref = self._get_or_create_actor_ref(agent_id)
                    retry_msg = AgentTaskMessage(
                        agent_id=agent_id,
                        task_id=task_id,
                        trace_id=self._trace_id,
                        task_path=self._base_task_path,
                        content=task_info["parameters"],
                        description=task_info["spec"].description,
                        user_id=self.current_user_id,
                        reply_to=self.myAddress,
                        context={},
                        is_parameter_completion=False,
                        parameters={}
                    )
                    self.send(agent_ref, retry_msg)
                except Exception as retry_e:
                    self._mark_final_failure(task_id, f"Retry failed during delegation: {retry_e}")
            else:
                self._mark_final_failure(task_id, f"Retry failed: original task info lost. Error: {error}")
        else:
            self._mark_final_failure(task_id, f"Max retries reached. Last error: {error}")

    def _mark_final_failure(self, task_id: str, error: str) -> None:
        logger.error(f"Task {task_id} finally failed: {error}")
        self._failed_tasks[task_id] = error
        self._pending_tasks.pop(task_id, None)
        self._check_completion()

    def _check_completion(self) -> None:
        """检查是否所有任务都结束了，并向上游报告最终状态"""
        if not self._pending_tasks:
            # ✅ 必须确保上下文字段存在
            if self._root_task_id is None or self._trace_id is None or self._base_task_path is None:
                logger.error("Missing root context when completing! Cannot send TaskCompletedMessage.")
                self.send(self.myAddress, ActorExitRequest())
                return

            if self._failed_tasks:
                # 有失败任务 → 整体失败
                first_failed = next(iter(self._failed_tasks))
                error_msg = self._failed_tasks[first_failed]
                self.send(self._creator, TaskCompletedMessage(
                    task_id=self._root_task_id,
                    trace_id=self._trace_id,
                    task_path=self._base_task_path,
                    message_type=MessageType.TASK_COMPLETED,
                    result=None,
                    status="FAILED",
                    agent_id=None
                ))
            elif len(self._completed_tasks) == 1:
                # 单个成功
                result = next(iter(self._completed_tasks.values()))
                self.send(self._creator, TaskCompletedMessage(
                    task_id=self._root_task_id,
                    trace_id=self._trace_id,
                    task_path=self._base_task_path,
                    message_type=MessageType.TASK_COMPLETED,
                    result=result,
                    status="SUCCESS",
                    agent_id=None
                ))
            else:
                # 多个结果（batch）
                self.send(self._creator, TaskCompletedMessage(
                    task_id=self._root_task_id,
                    trace_id=self._trace_id,
                    task_path=self._base_task_path,
                    message_type=MessageType.TASK_COMPLETED,
                    result=self._completed_tasks,
                    status="SUCCESS",
                    agent_id=None
                ))

            self.send(self.myAddress, ActorExitRequest())

    def _send_error_to_creator(self, error: str) -> None:
        """发送系统级错误（如内部异常）给创建者"""
        if self._creator and self._root_task_id and self._trace_id and self._base_task_path:
            self.send(self._creator, TaskCompletedMessage(
                task_id=self._root_task_id,          # ✅ 修正：原来是 self._task_id（不存在）
                trace_id=self._trace_id,
                task_path=self._base_task_path,
                message_type=MessageType.TASK_COMPLETED,
                result=None,
                status="ERROR",
                agent_id=None
            ))
        else:
            logger.warning("Cannot send error to creator: missing context")

    def _is_leaf_node(self, agent_id: str) -> bool:
        """
        判断当前Agent是否为叶子节点
        通过TreeManager查询是否有子节点

        Args:
            agent_id: Agent节点ID

        Returns:
            bool: 是否为叶子节点
        """
        from agents.tree.tree_manager import TreeManager
        tree_manager = TreeManager()
        children = tree_manager.get_children(agent_id)
        return len(children) == 0

