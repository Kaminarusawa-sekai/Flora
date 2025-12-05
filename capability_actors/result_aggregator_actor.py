# capability_actors/result_aggregator_actor.py
from typing import Dict, Any, List, Optional
from datetime import datetime
from thespian.actors import Actor, ActorExitRequest
from common.messages.task_messages import (
    TaskCompleted, TaskFailed, ExecuteTaskMessage, TaskSpec, TaskMessage
)
# 假设 InitMessage 在 lifecycle_messages 中，如果位置不同请调整引用
from common.messages import InitMessage 
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
    3. 发送 TaskMessage 给 AgentActor 执行
    4. 负责执行过程中的 重试 (Retry) 和 超时 (Timeout) 管理
    5. 将最终结果返回给 TaskGroupAggregator
    """
    
    def __init__(self):
        super().__init__()
        self._pending_tasks: Dict[str, Any] = {}  # task_id -> task_info
        self._completed_tasks: Dict[str, Any] = {}  # task_id -> result
        self._failed_tasks: Dict[str, Any] = {}  # task_id -> error_info
        self._retries: Dict[str, int] = {}  # task_id -> retry_count
        
        # 新增：Actor 引用缓存
        self._actor_ref_cache: Dict[str, Any] = {}
        # 新增：Registry 对象 (需从 initialize 消息中获取)
        self.registry = None
        self.current_user_id = None
        self._max_retries = 3 
        self._timeout = 300 
        self._creator: Any = None 
        self._aggregation_strategy: str = "map_reduce" 
        self._trace_id: str = None 
    
    def receiveMessage(self, message: Any, sender: Any) -> None:
        """处理接收到的消息"""
        try:
            # 1. 处理字典类型的控制消息
            if isinstance(message, dict):
                msg_type = message.get("type")

                if msg_type == "initialize":
                    self._handle_initialize(message, sender)
                
                elif msg_type == "execute_subtask":
                    # 接收来自 TaskGroupAggregator 的 Agent 任务执行请求
                    self._handle_execute_subtask(message, sender)
                
                elif msg_type == "get_final_result":
                    self._handle_get_final_result(message, sender)
                
                # 兼容旧的字典返回格式
                elif msg_type == "subtask_result":
                    self._handle_subtask_result(message, sender)
                elif msg_type == "subtask_error":
                    self._handle_subtask_error(message, sender)
                    
            # 2. 处理标准对象类型的返回消息
            elif isinstance(message, TaskCompleted):
                self._handle_task_completed_obj(message, sender)
                
            elif isinstance(message, TaskFailed):
                self._handle_task_failed_obj(message, sender)
                
            # 3. 兼容旧的类消息
            elif isinstance(message, (SubtaskResultMessage, SubtaskErrorMessage)):
                self._handle_legacy_message(message, sender)
                
            else:
                logger.warning(f"Unknown message type: {type(message)}")
                
        except Exception as e:
            logger.error(f"ResultAggregatorActor execution failed: {e}", exc_info=True)
            self._send_error_to_creator(str(e))

    def _handle_initialize(self, msg: Dict[str, Any], sender: Any) -> None:
        """初始化聚合器"""
        self._creator = sender
        self._trace_id = msg.get("trace_id", f"trace_{datetime.now().strftime('%Y%m%d%H%M%S')}")
        self._max_retries = msg.get("max_retries", self._max_retries)
        self._timeout = msg.get("timeout", self._timeout)
        self._aggregation_strategy = msg.get("aggregation_strategy", "sequential")
        

        from agents.tree.tree_manager import treeManager
        # 获取 Registry，用于后续创建 AgentActor
        self.registry = treeManager
        
        # 如果初始化时带了 pending_tasks
        pending_tasks = msg.get("pending_tasks", [])
        for task_id in pending_tasks:
            self._pending_tasks[task_id] = {}
            self._retries[task_id] = 0
            
        logger.info(f"ResultAggregator initialized. Trace: {self._trace_id}, Pending: {len(pending_tasks)}")

    def _get_or_create_actor_ref(self, agent_id: str):
        """
        获取或创建 AgentActor 引用，并在创建时发送初始化消息
        """
        if agent_id not in self._actor_ref_cache:
            if not self.registry:
                raise ValueError("Registry not initialized in ResultAggregator")
            from agents.agent_actor import AgentActor
            # 创建 Actor
            ref = self.createActor(AgentActor)
            
            # 从 registry 获取完整配置
            agent_info = self.registry.get_agent_meta(agent_id)
            if not agent_info:
                # 如果 Registry 里没找到，尝试只用 agent_id 初始化，或者报错
                # 这里假设必须存在于 Registry
                logger.warning(f"Agent {agent_id} not found in registry, using defaults.")
                capabilities = ["default"]
            else:
                capabilities = agent_info.get("capability", [])

            # 构造 InitMessage
            # init_msg = InitMessage(
            #     agent_id=agent_id,
            #     capabilities=capabilities,
            #     memory_key=agent_id, # 默认 = agent_id
            #     registry=self.registry,
            # )
            init_msg = {
                "message_type": "init",
                "agent_id": agent_id
            }
            
            # 发送初始化消息
            self.send(ref, init_msg)
            
            # 缓存引用
            self._actor_ref_cache[agent_id] = ref
            logger.info(f"Created new AgentActor for {agent_id}")

        return self._actor_ref_cache[agent_id]

    def _handle_execute_subtask(self, msg: Dict[str, Any], sender: Any) -> None:
        """
        ⑩ 执行子任务 - 修改为直接分发给 AgentActor
        """
        # 提取参数
        task_id = msg.get("task_id")
        task_spec: TaskSpec = msg.get("task_spec") 
        parameters = msg.get("parameters", {})
        description = task_spec.description
        self.current_user_id = msg.get("user_id", None)
        
        # executor 在这里对应具体的 agent_id (例如 "poster_designer_v2")
        agent_id = msg.get("executor") 
        
        if not agent_id:
            # 如果没有指定 executor，尝试从 node_id 获取，或者报错
            agent_id = msg.get("node_id")
            if not agent_id:
                self._process_failure(task_id, "Missing 'executor' or 'node_id' in execute request", sender)
                return

        logger.info(f"⑩ ResultAggregator: Delegating Task {task_id} to AgentActor: {agent_id}")

        # 1. 注册任务状态
        if task_id not in self._pending_tasks:
            self._pending_tasks[task_id] = {
                "spec": task_spec,
                "executor": agent_id,
                "parameters": parameters
            }
            self._retries[task_id] = 0

        try:
            # 2. 获取或创建 AgentActor 引用
            agent_ref = self._get_or_create_actor_ref(agent_id)
            
            # 3. 构造 TaskMessage (child_ctx)
            # parameters 作为上下文传递给 Agent
            # 注意：这里根据您的需求使用 TaskMessage(task_id, context)
            task_msg = {
                "message_type": "agent_task",
                "task_id": task_id,
                "content": task_spec.params,
                "description": description,
                "user_id": self.current_user_id,
                "reply_to": self.myAddress  # 让后台回复给InteractionActor
            }
            
            # 4. 发送给 AgentActor
            self.send(agent_ref, task_msg)
            
        except Exception as e:
            logger.error(f"Failed to spawn agent task {task_id}: {e}", exc_info=True)
            self._process_failure(task_id, str(e), sender)

    # ----------------------------------------------------------------
    # 结果处理逻辑 (处理来自 AgentActor 的返回)
    # ----------------------------------------------------------------

    def _handle_task_completed_obj(self, msg: TaskCompleted, sender: Any) -> None:
        """处理标准的 TaskCompleted 对象"""
        logger.info(f"Received TaskCompleted for {msg.task_id}")
        self._process_success(msg.task_id, msg.result)

    def _handle_task_failed_obj(self, msg: TaskFailed, sender: Any) -> None:
        """处理标准的 TaskFailed 对象"""
        logger.info(f"Received TaskFailed for {msg.task_id}: {msg.error}")
        self._process_failure(msg.task_id, msg.error, sender)

    def _handle_subtask_result(self, msg: Dict[str, Any], sender: Any) -> None:
        """处理字典格式的成功消息"""
        self._process_success(msg.get("task_id"), msg.get("result"))

    def _handle_subtask_error(self, msg: Dict[str, Any], sender: Any) -> None:
        """处理字典格式的失败消息"""
        self._process_failure(msg.get("task_id"), msg.get("error"), sender)

    def _handle_legacy_message(self, msg: Any, sender: Any) -> None:
        """处理旧的消息类"""
        if hasattr(msg, "result"):
            self._process_success(msg.task_id, msg.result)
        elif hasattr(msg, "error"):
            self._process_failure(msg.task_id, msg.error, sender)
    
    def _handle_get_final_result(self, msg: Dict[str, Any], sender: Any) -> None:
        """手动触发结果检查"""
        self._check_completion()

    # ----------------------------------------------------------------
    # 核心逻辑：成功与失败(重试)
    # ----------------------------------------------------------------

    def _process_success(self, task_id: str, result: Any) -> None:
        """统一的成功处理逻辑"""
        if not task_id: 
            return

        # 移除 pending
        if task_id in self._pending_tasks:
            del self._pending_tasks[task_id]
        if task_id in self._failed_tasks:
            del self._failed_tasks[task_id]
            
        self._completed_tasks[task_id] = result
        
        # 检查是否全部完成
        self._check_completion()

    def _process_failure(self, task_id: str, error: str, worker_sender: Any) -> None:
        """统一的失败处理逻辑 (包含重试)"""
        if not task_id:
            return

        current_retry = self._retries.get(task_id, 0)
        
        if current_retry < self._max_retries:
            # === 执行重试 ===
            self._retries[task_id] = current_retry + 1
            logger.warning(f"Task {task_id} failed. Retrying ({self._retries[task_id]}/{self._max_retries}). Error: {error}")
            
            task_info = self._pending_tasks.get(task_id)
            if task_info:
                # 获取原任务信息
                agent_id = task_info.get("executor")
                parameters = task_info.get("parameters")
                
                try:
                    # 重新获取 Agent 并发送消息
                    # 注意：如果 Agent 挂了，_get_or_create_actor_ref 会重新创建
                    agent_ref = self._get_or_create_actor_ref(agent_id)
                    
                    retry_msg = TaskMessage(
                        task_id=task_id,
                        context=parameters
                    )
                    self.send(agent_ref, retry_msg)
                except Exception as retry_e:
                     self._mark_final_failure(task_id, f"Retry failed during delegation: {retry_e}")
            else:
                self._mark_final_failure(task_id, f"Retry failed: original task info lost. Error: {error}")

        else:
            # === 超过重试次数 ===
            self._mark_final_failure(task_id, f"Max retries reached. Last error: {error}")

    def _mark_final_failure(self, task_id: str, error: str) -> None:
        """标记最终失败"""
        logger.error(f"Task {task_id} finally failed: {error}")
        self._failed_tasks[task_id] = error
        if task_id in self._pending_tasks:
            del self._pending_tasks[task_id]
        self._check_completion()

    def _check_completion(self) -> None:
        """检查是否所有任务都结束了"""
        if not self._pending_tasks:
            # 构造标准的 TaskCompleted 消息给 TaskGroupAggregator
            if len(self._completed_tasks) == 1:
                first_key = next(iter(self._completed_tasks))
                final_output = self._completed_tasks[first_key]
                
                self.send(self._creator, TaskCompleted(
                    source=self.myAddress,
                    destination=self._creator,
                    task_id=self._trace_id, # 这里用 trace_id 对应 parent_task_id
                    result=final_output,
                    original_spec=None
                ))
            elif self._failed_tasks:
                 first_key = next(iter(self._failed_tasks))
                 self.send(self._creator, TaskFailed(
                     source=self.myAddress,
                     destination=self._creator,
                     task_id=self._trace_id,
                     error=self._failed_tasks[first_key]
                 ))
            else:
                # 多个结果（如果用了 batch），返回字典
                self.send(self._creator, TaskCompleted(
                    source=self.myAddress,
                    destination=self._creator,
                    task_id=self._trace_id,
                    result=self._completed_tasks,
                    original_spec=None
                ))

            self.send(self.myAddress, ActorExitRequest())

    def _send_error_to_creator(self, error: str) -> None:
        if self._creator:
            self.send(self._creator, TaskFailed(source=self.myAddress, destination=self._creator, task_id=self._trace_id, error=error))

# 兼容旧类定义
class SubtaskResultMessage:
    def __init__(self, task_id: str, result: Any):
        self.task_id = task_id
        self.result = result

class SubtaskErrorMessage:
    def __init__(self, task_id: str, error: str):
        self.task_id = task_id
        self.error = error