"""
TaskRouterActor - 统一任务路由层（Actor 模式）

职责：
1. 统一入口：处理新任务和恢复任务
2. 任务状态管理：维护任务状态到 Redis
3. 异步接收结果：通过 receiveMessage 接收 TaskCompletedMessage
4. 结果发布：将任务结果发布到 RabbitMQ 供 interaction 服务消费

架构：
    API Server ──tell──► TaskRouterActor ──tell──► AgentActor ──► ... ──► LeafActor
         │                      │                                              │
         └── 立即返回 202       └◄──────── TaskCompletedMessage ◄──────────────┘
                                │
                                ▼
                          RabbitMQ (task.result)
"""
import logging
import uuid
from typing import Any, Dict, Optional
from dataclasses import dataclass

from thespian.actors import Actor, ActorSystem, ActorAddress, ActorExitRequest

from common.messages.task_messages import (
    AgentTaskMessage,
    ResumeTaskMessage,
    TaskCompletedMessage
)
from external.repositories.task_state_repo import (
    TaskStateRepository,
    TaskState,
    TaskStatus,
    PausedLayer,
    get_task_state_repo
)
from external.message_queue.task_result_publisher import (
    TaskResultPublisher,
    get_task_result_publisher
)

logger = logging.getLogger(__name__)


# ==================== 消息定义 ====================

@dataclass
class RouterNewTaskMessage:
    """路由新任务消息"""
    user_input: str
    user_id: str
    agent_id: Optional[str] = None
    task_id: Optional[str] = None
    trace_id: Optional[str] = None
    task_path: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    global_context: Optional[Dict[str, Any]] = None


@dataclass
class RouterResumeTaskMessage:
    """路由恢复任务消息"""
    trace_id: str
    parameters: Dict[str, Any]
    user_id: str


@dataclass
class RouterGetStatusMessage:
    """查询任务状态消息"""
    trace_id: str


@dataclass
class RouterCancelTaskMessage:
    """取消任务消息"""
    trace_id: str


@dataclass
class RouterStatusResponse:
    """状态查询响应"""
    found: bool
    status: Optional[Dict[str, Any]] = None


@dataclass
class RouterCancelResponse:
    """取消任务响应"""
    success: bool


@dataclass
class RouterTaskAccepted:
    """任务已接受响应"""
    task_id: str
    trace_id: str


@dataclass
class RouterResumeAccepted:
    """恢复任务已接受响应"""
    trace_id: str
    success: bool
    error: Optional[str] = None


# ==================== TaskRouterActor ====================

class TaskRouterActor(Actor):
    """
    任务路由器 Actor

    作为 Tasks 服务的统一入口，负责：
    1. 接收来自 API 的任务请求（通过 tell）
    2. 路由新任务到 AgentActor
    3. 路由恢复任务到正确的 Actor
    4. 接收 TaskCompletedMessage 并发布到 RabbitMQ
    5. 管理任务状态
    """

    def __init__(self):
        super().__init__()
        self._state_repo: Optional[TaskStateRepository] = None
        self._result_publisher: Optional[TaskResultPublisher] = None
        self._agent_actor_ref: Optional[ActorAddress] = None
        self._enable_rabbitmq_publish: bool = True
        self._initialized: bool = False

        # 活跃任务映射: trace_id -> user_id（用于结果发布时获取 user_id）
        self._active_tasks: Dict[str, str] = {}

        self._logger = logging.getLogger("TaskRouterActor")

    def _ensure_initialized(self):
        """确保已初始化（懒加载）"""
        if self._initialized:
            return

        self._state_repo = get_task_state_repo()

        if self._enable_rabbitmq_publish:
            try:
                self._result_publisher = get_task_result_publisher()
                self._result_publisher.connect()
                self._logger.info("TaskResultPublisher initialized")
            except Exception as e:
                self._logger.warning(f"Failed to initialize TaskResultPublisher: {e}")
                self._result_publisher = None

        self._initialized = True

    def _ensure_agent_actor(self) -> ActorAddress:
        """确保 AgentActor 已创建"""
        if self._agent_actor_ref is None:
            from agents.agent_actor import AgentActor
            self._agent_actor_ref = self.createActor(AgentActor)
            self._logger.info("Created AgentActor")
        return self._agent_actor_ref

    def _get_default_agent_id(self) -> str:
        """获取默认的根 Agent ID"""
        try:
            from agents.tree.tree_manager import treeManager
            root_agents = treeManager.get_root_agents()
            return root_agents[0] if root_agents else "agent_root"
        except Exception:
            return "agent_root"

    def receiveMessage(self, message: Any, sender: ActorAddress):
        """接收并处理消息"""
        self._ensure_initialized()

        if isinstance(message, ActorExitRequest):
            self._logger.info("Received ActorExitRequest, shutting down.")
            return

        try:
            if isinstance(message, RouterNewTaskMessage):
                self._handle_new_task(message, sender)
            elif isinstance(message, RouterResumeTaskMessage):
                self._handle_resume_task(message, sender)
            elif isinstance(message, RouterGetStatusMessage):
                self._handle_get_status(message, sender)
            elif isinstance(message, RouterCancelTaskMessage):
                self._handle_cancel_task(message, sender)
            elif isinstance(message, TaskCompletedMessage):
                self._handle_task_completed(message, sender)
            else:
                self._logger.warning(f"Unknown message type: {type(message)}")
        except Exception as e:
            self._logger.exception(f"Error in TaskRouterActor: {e}")

    # ==================== 消息处理 ====================

    def _handle_new_task(self, msg: RouterNewTaskMessage, sender: ActorAddress):
        """处理新任务请求"""
        # 生成 ID
        task_id = msg.task_id or str(uuid.uuid4())
        trace_id = msg.trace_id or task_id
        task_path = msg.task_path or "/"
        agent_id = msg.agent_id or self._get_default_agent_id()

        self._logger.info(f"Handling new task: {task_id}, agent={agent_id}, trace_id={trace_id}")

        # 保存 user_id 用于结果发布
        self._active_tasks[trace_id] = msg.user_id

        # 构造消息，设置 reply_to 为自己
        agent_msg = AgentTaskMessage(
            task_id=task_id,
            trace_id=trace_id,
            task_path=task_path,
            agent_id=agent_id,
            content=msg.user_input,
            description=msg.user_input,
            user_id=msg.user_id,
            parameters=msg.parameters or {},
            global_context=msg.global_context or {},
            reply_to=self.myAddress  # 关键：设置回调地址为自己
        )

        # 保存初始状态
        self._state_repo.save_state(TaskState(
            task_id=task_id,
            trace_id=trace_id,
            task_path=task_path,
            status=TaskStatus.RUNNING,
            user_id=msg.user_id,
            agent_id=agent_id,
            original_content=msg.user_input,
            original_description=msg.user_input,
            global_context=msg.global_context or {},
            parameters=msg.parameters or {}
        ))

        # 异步发送到 AgentActor（不等待）
        agent_ref = self._ensure_agent_actor()
        self.send(agent_ref, agent_msg)

        # 立即回复 API：任务已接受
        self.send(sender, RouterTaskAccepted(task_id=task_id, trace_id=trace_id))

    def _handle_resume_task(self, msg: RouterResumeTaskMessage, sender: ActorAddress):
        """处理恢复任务请求"""
        self._logger.info(f"Handling resume task: trace_id={msg.trace_id}")

        # 1. 从 Redis 加载任务状态
        state = self._state_repo.get_state(msg.trace_id)
        if not state:
            self._logger.error(f"Task state not found: trace_id={msg.trace_id}")
            self.send(sender, RouterResumeAccepted(
                trace_id=msg.trace_id,
                success=False,
                error=f"Task with trace_id={msg.trace_id} not found or expired"
            ))
            return

        if state.status != TaskStatus.NEED_INPUT:
            self._logger.warning(f"Task trace_id={msg.trace_id} is not in NEED_INPUT status: {state.status}")
            self.send(sender, RouterResumeAccepted(
                trace_id=msg.trace_id,
                success=False,
                error=f"Task with trace_id={msg.trace_id} is not waiting for input (status: {state.status.value})"
            ))
            return

        # 2. 合并参数
        merged_params = (state.parameters or {}).copy()
        merged_params.update(msg.parameters)

        # 3. 更新状态为 RUNNING
        self._state_repo.update_status(msg.trace_id, TaskStatus.RUNNING, {
            "parameters": merged_params
        })

        # 4. 保存 user_id
        self._active_tasks[msg.trace_id] = msg.user_id

        # 5. 构造恢复消息
        resume_msg = ResumeTaskMessage(
            task_id=state.task_id,
            trace_id=state.trace_id,
            task_path=state.task_path,
            parameters=merged_params,
            user_id=msg.user_id,
            reply_to=self.myAddress  # 关键：设置回调地址为自己
        )

        # 6. 异步发送到 AgentActor
        agent_ref = self._ensure_agent_actor()
        self.send(agent_ref, resume_msg)

        # 7. 立即回复 API：恢复请求已接受
        self.send(sender, RouterResumeAccepted(trace_id=msg.trace_id, success=True))

    def _handle_get_status(self, msg: RouterGetStatusMessage, sender: ActorAddress):
        """处理状态查询请求"""
        state = self._state_repo.get_state(msg.trace_id)
        if state:
            self.send(sender, RouterStatusResponse(found=True, status=state.to_dict()))
        else:
            self.send(sender, RouterStatusResponse(found=False))

    def _handle_cancel_task(self, msg: RouterCancelTaskMessage, sender: ActorAddress):
        """处理取消任务请求"""
        success = self._state_repo.update_status(msg.trace_id, TaskStatus.CANCELLED)
        self.send(sender, RouterCancelResponse(success=success))

    def _handle_task_completed(self, msg: TaskCompletedMessage, sender: ActorAddress):
        """
        处理任务完成消息

        这是核心方法：当 AgentActor 完成任务后，会发送 TaskCompletedMessage 到这里
        """
        trace_id = msg.trace_id
        task_id = msg.task_id
        status = msg.status
        task_path = msg.task_path

        self._logger.info(f"Received TaskCompletedMessage: trace_id={trace_id}, status={status}")

        # 获取 user_id
        user_id = self._active_tasks.get(trace_id, "")

        # 根据状态更新 Redis 并发布到 RabbitMQ
        if status == "SUCCESS":
            self._state_repo.update_status(trace_id, TaskStatus.COMPLETED)
            self._publish_result_to_rabbitmq(
                trace_id=trace_id,
                task_id=task_id,
                status="SUCCESS",
                result=msg.result,
                task_path=task_path,
                user_id=user_id
            )
            # 清理活跃任务
            self._active_tasks.pop(trace_id, None)

        elif status == "NEED_INPUT":
            result_data = msg.result or {}
            self._state_repo.update_status(trace_id, TaskStatus.NEED_INPUT, {
                "missing_params": result_data.get("missing_params"),
                "paused_step": result_data.get("step")
            })
            self._publish_result_to_rabbitmq(
                trace_id=trace_id,
                task_id=task_id,
                status="NEED_INPUT",
                result=result_data,
                task_path=task_path,
                user_id=user_id
            )
            # 不清理活跃任务，等待恢复

        else:  # FAILED, ERROR, CANCELLED
            self._state_repo.update_status(trace_id, TaskStatus.FAILED)
            error_msg = msg.result.get("error") if isinstance(msg.result, dict) else str(msg.result)
            self._publish_result_to_rabbitmq(
                trace_id=trace_id,
                task_id=task_id,
                status=status,
                result=msg.result,
                error=error_msg,
                task_path=task_path,
                user_id=user_id
            )
            # 清理活跃任务
            self._active_tasks.pop(trace_id, None)

    def _publish_result_to_rabbitmq(
        self,
        trace_id: str,
        task_id: str,
        status: str,
        result: Any,
        error: Optional[str] = None,
        task_path: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> None:
        """发布任务结果到 RabbitMQ"""
        if not self._enable_rabbitmq_publish or not self._result_publisher:
            return

        try:
            self._result_publisher.publish_result(
                trace_id=trace_id,
                task_id=task_id,
                status=status,
                result=result,
                error=error,
                task_path=task_path,
                user_id=user_id
            )
            self._logger.info(f"Published result to RabbitMQ: trace_id={trace_id}, status={status}")
        except Exception as e:
            self._logger.error(f"Failed to publish result to RabbitMQ: {e}")


# ==================== 辅助类：同步 API 包装器 ====================

class TaskRouterClient:
    """
    TaskRouterActor 的同步客户端

    用于 API Server 与 TaskRouterActor 通信
    """

    def __init__(self, actor_system: ActorSystem, router_actor: ActorAddress):
        self._actor_system = actor_system
        self._router_actor = router_actor
        self._logger = logging.getLogger("TaskRouterClient")

    def submit_new_task(
        self,
        user_input: str,
        user_id: str,
        agent_id: Optional[str] = None,
        task_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        task_path: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
        global_context: Optional[Dict[str, Any]] = None,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """
        提交新任务（异步模式）

        Returns:
            Dict: {"accepted": True, "task_id": "...", "trace_id": "..."} 或错误信息
        """
        msg = RouterNewTaskMessage(
            user_input=user_input,
            user_id=user_id,
            agent_id=agent_id,
            task_id=task_id,
            trace_id=trace_id,
            task_path=task_path,
            parameters=parameters,
            global_context=global_context
        )

        response = self._actor_system.ask(self._router_actor, msg, timeout=timeout)

        if isinstance(response, RouterTaskAccepted):
            return {
                "accepted": True,
                "task_id": response.task_id,
                "trace_id": response.trace_id
            }
        else:
            return {
                "accepted": False,
                "error": f"Unexpected response: {response}"
            }

    def submit_resume_task(
        self,
        trace_id: str,
        parameters: Dict[str, Any],
        user_id: str,
        timeout: float = 5.0
    ) -> Dict[str, Any]:
        """
        提交恢复任务请求（异步模式）

        Returns:
            Dict: {"accepted": True, "trace_id": "..."} 或错误信息
        """
        msg = RouterResumeTaskMessage(
            trace_id=trace_id,
            parameters=parameters,
            user_id=user_id
        )

        response = self._actor_system.ask(self._router_actor, msg, timeout=timeout)

        if isinstance(response, RouterResumeAccepted):
            if response.success:
                return {
                    "accepted": True,
                    "trace_id": response.trace_id
                }
            else:
                return {
                    "accepted": False,
                    "error": response.error
                }
        else:
            return {
                "accepted": False,
                "error": f"Unexpected response: {response}"
            }

    def get_task_status(self, trace_id: str, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """获取任务状态"""
        msg = RouterGetStatusMessage(trace_id=trace_id)
        response = self._actor_system.ask(self._router_actor, msg, timeout=timeout)

        if isinstance(response, RouterStatusResponse):
            return response.status if response.found else None
        return None

    def cancel_task(self, trace_id: str, timeout: float = 5.0) -> bool:
        """取消任务"""
        msg = RouterCancelTaskMessage(trace_id=trace_id)
        response = self._actor_system.ask(self._router_actor, msg, timeout=timeout)

        if isinstance(response, RouterCancelResponse):
            return response.success
        return False


# ==================== 单例管理 ====================

_task_router_actor: Optional[ActorAddress] = None
_task_router_client: Optional[TaskRouterClient] = None
_actor_system_ref: Optional[ActorSystem] = None


def init_task_router(actor_system: ActorSystem) -> TaskRouterClient:
    """
    初始化 TaskRouterActor 并返回客户端

    Args:
        actor_system: Actor 系统

    Returns:
        TaskRouterClient: 路由器客户端
    """
    global _task_router_actor, _task_router_client, _actor_system_ref

    _actor_system_ref = actor_system
    _task_router_actor = actor_system.createActor(TaskRouterActor)
    _task_router_client = TaskRouterClient(actor_system, _task_router_actor)

    logger.info("TaskRouterActor initialized")
    return _task_router_client


def get_task_router(actor_system: Optional[ActorSystem] = None) -> TaskRouterClient:
    """
    获取 TaskRouterClient 单例

    Args:
        actor_system: Actor 系统（首次调用时必须提供）

    Returns:
        TaskRouterClient: 路由器客户端
    """
    global _task_router_client
    if _task_router_client is None:
        if actor_system is None:
            raise ValueError("actor_system is required for first initialization")
        return init_task_router(actor_system)
    return _task_router_client


def get_task_router_actor() -> Optional[ActorAddress]:
    """获取 TaskRouterActor 地址（用于直接 tell）"""
    return _task_router_actor


# ==================== 兼容旧接口 ====================

# 为了兼容性，保留 TaskRouter 别名
TaskRouter = TaskRouterClient
