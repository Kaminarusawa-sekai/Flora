"""Agent Actor - 智能体执行器
负责处理任务分发、子任务协调和结果聚合
集成并行执行管理器，支持任务的并行处理
"""
import logging
from typing import Any, Dict, Set, Optional
from thespian.actors import Actor, ActorAddress

from new.agents.parallel.execution_manager import (
    ParallelExecutionManager
)
from new.agents.coordination.task_coordinator import TaskCoordinator
from new.capabilities.routing.task_router import TaskRouter
from new.agents.execution.result_aggregator import ResultAggregator
from new.agents.tree.tree_manager import TreeManager
from new.events.event_bus import event_bus
from new.events.event_types import EventType

# 从common.messages导入所需的消息类
from new.common.messages import (
    InitMessage,
    AgentTaskMessage as TaskMessage,
    SubtaskResultMessage,
    SubtaskErrorMessage,
    MemoryResponseMessage,
    DifySchemaRequest,
    DifySchemaResponse,
    DifyExecuteRequest,
    DifyExecuteResponse,
    DataQueryRequest,
    DataQueryResponse,
    McpFallbackRequest
)

# 导入数据actor
from new.capability_actors.data_actor import DataActor

class AgentActor(Actor):
    """智能体执行器，集成并行执行管理器"""
    
    def __init__(self):
        self.agent_id = None
        self.agent_name = None
        self.max_concurrency = None
        self.capabilities = []
        self._self_info = {}
        self._pending_memory_requests = {}
        self._pending_data_requests = {}
        self._pending_execution_requests = {}
        self._aggregation_state = {}
        self._actor_ref_cache = {}
        self.registry = None
        self._data_query_actor = None
        self._execution_actor = None  # 执行actor引用
        self._data_actor = None       # 数据actor引用
        self.orchestrator = None
        self._task_coordinator = None
        self._task_router = None
        self._parallel_execution_manager = None
        self._tree_manager = None
        self.parallel_executor = None
        self.task_coordinator = None
        self.tree_manager = None
        
    def receiveMessage(self, message: Any, sender: ActorAddress):
        """处理接收到的消息"""
        if isinstance(message, InitMessage):
            self._initialize(message, sender)
        elif isinstance(message, TaskMessage):
            self._handle_task(message, sender)
        elif isinstance(message, MemoryResponseMessage):
            self._handle_memory_response(message.key, message.value, sender)
        elif isinstance(message, SubtaskResultMessage):
            self._handle_subtask_completion(message.task_id, message.result, sender)
        elif isinstance(message, SubtaskErrorMessage):
            self._handle_subtask_error(message.task_id, message.error, sender)
        elif isinstance(message, DifySchemaResponse):
            self._handle_dify_schema_response(message, sender)
        elif isinstance(message, DifyExecuteResponse):
            self._handle_dify_execute_response(message)
        elif isinstance(message, DataQueryResponse):
            self._handle_data_response(message)
        elif isinstance(message, SubtaskResultMessage):
            self._handle_execution_result(message, sender)
        elif isinstance(message, SubtaskErrorMessage):
            self._handle_execution_error(message, sender)
        else:
            logging.warning(f"Unknown message type: {type(message)}")
    
    def _initialize(self, msg: InitMessage, sender: ActorAddress):
        """初始化智能体"""
        self.agent_id = msg.agent_id
        self.capabilities = msg.capabilities
        self.registry = msg.registry
        
        # 创建执行actor实例
        from new.capability_actors.execution_actor import ExecutionActor
        self._execution_actor = self.createActor(ExecutionActor)
        
        # 创建数据actor实例
        self._data_actor = self.createActor(DataActor)
        
        # 初始化并行执行管理器
        self._parallel_execution_manager = ParallelExecutionManager()
        self.parallel_executor = self._parallel_execution_manager
        
        # 初始化任务协调器
        self._task_coordinator = TaskCoordinator()
        self.task_coordinator = self._task_coordinator
        
        # 初始化任务路由器
        self._task_router = TaskRouter()
        self._task_router.initialize(self.registry)
        
        # 初始化树管理器
        self._tree_manager = TreeManager()
        self.tree_manager = self._tree_manager
        
        # 初始化其他组件...
        self._self_info = {}
        self._data_query_actor = None
        self.orchestrator = None
        
        logging.info(f"Agent {self.agent_id} initialized with capabilities: {self.capabilities}")
        logging.info(f"Created execution_actor: {self._execution_actor}, data_actor: {self._data_actor}")
    
    def receiveMessage(self, message: Any, sender: ActorAddress):
        """处理接收到的消息"""
        if isinstance(message, InitMessage):
            self._initialize(message, sender)
        elif isinstance(message, TaskMessage):
            self._handle_task(message, sender)
        elif isinstance(message, StateQueryMessage):
            self._handle_state_query(message, sender)
        elif isinstance(message, ResetStateMessage):
            self._handle_reset(message, sender)
        # 其他消息类型处理...
    
    def _handle_task(self, task_msg: TaskMessage, sender: ActorAddress):
        """处理接收到的任务"""
        self._report_event("started", task_msg.task_id, {"context_preview": str(task_msg.context)[:200]})
        
        # 使用并行执行管理器判断任务类型并处理
        if self._is_leaf_task(task_msg.context):
            # 叶子任务：直接执行
            self._execute_leaf_task(task_msg.task_id, task_msg.context, {}, sender)
        else:
            # 中间任务：创建子任务并协调执行
            self._execute_intermediate(task_msg.task_id, task_msg.context, sender)
    
    def _is_leaf_task(self, context: Dict) -> bool:
        """判断是否为叶子任务"""
        # 简化实现：根据任务协调器的判断结果
        return self._task_coordinator.is_leaf_task(self.agent_id, context)
    
    def _execute_leaf_task(self, task_id: str, context: Dict, memory: Dict, sender: ActorAddress, capability: str = "dify_workflow"):
        """执行叶子任务 - 直接委托给execution_actor"""
        # 构造执行请求
        execution_request = {
            "type": "leaf_task",
            "task_id": task_id,
            "context": context,
            "memory": memory,
            "capability": capability,
            "agent_id": self.agent_id
        }
        
        # 保存执行请求信息，以便在执行完成后处理响应
        self._pending_execution_requests[task_id] = {
            "original_sender": sender
        }
        
        # 发送执行请求给execution_actor
        self.send(self._execution_actor, execution_request)
        self._report_event("execution_request_sent", task_id, {
            "capability": capability
        })
    
    def _execute_capability_fn(self, capability: str, context: Dict, memory: Dict) -> Any:
        """执行特定能力函数"""
        # 这里会使用并行执行管理器执行能力函数
        return self._parallel_execution_manager.execute_capability(
            capability=capability,
            context=context,
            memory=memory
        )
    
    def _handle_memory_response(self, key: str, memory_value: Any, sender: ActorAddress):
        """处理记忆响应"""
        if not self._pending_memory_requests:
            return
        
        task_id, task_info = next(iter(self._pending_memory_requests.items()))
        del self._pending_memory_requests[task_id]
        
        memory = {"user_pref": memory_value} if memory_value else {}
        
        # 根据能力类型决定下一步操作
        if task_info["capability"] == "book_flight":
            self._fetch_data_for_task(
                task_id=task_id,
                query="SELECT * FROM flights WHERE user='alice'",
                capability=task_info["capability"],
                context=task_info["context"],
                memory=memory,
                sender=task_info["sender"]
            )
        else:
            self._execute_leaf_task(
                task_id, task_info["capability"], task_info["context"], memory, task_info["sender"]
            )
    
    def _fetch_data_for_task(self, task_id: str, query: str, capability: str, context: Dict, memory: Dict, sender: ActorAddress):
        """为任务获取数据"""
        request_id = f"data_req_{task_id}"
        self._pending_data_requests[request_id] = {
            "task_id": task_id,
            "sender": sender,
            "context": context,
            "memory": memory,
            "capability": capability
        }
        
        # 使用并行执行管理器发送数据查询
        self._parallel_execution_manager.execute_data_query(
            request_id=request_id,
            query=query,
            data_actor=self._data_query_actor
        )
    
    def _handle_data_response(self, response: DataQueryResponse):
        """处理数据查询响应"""
        req_id = response.request_id
        if req_id not in self._pending_data_requests:
            logging.warning(f"Orphaned data response for {req_id}")
            return

        info = self._pending_data_requests.pop(req_id)
        if response.error:
            self.send(info["sender"], SubtaskErrorMessage(info["task_id"], response.error))
            return

        enhanced_context = {**info["context"], "db_result": response.result}
        self._execute_leaf_task(
            info["task_id"], enhanced_context, info["memory"], info["sender"], info["capability"]
        )

    def _handle_execution_result(self, msg: SubtaskResultMessage, sender: ActorAddress) -> None:
        """Handle execution result from execution_actor"""
        task_id = msg.task_id
        if task_id in self._pending_execution_requests:
            original_sender = self._pending_execution_requests.pop(task_id)["original_sender"]
            self.send(original_sender, msg)
            self._report_event("finished", task_id, {"result_preview": str(msg.result)[:200]})
        else:
            logging.warning(f"Orphaned execution result for task: {task_id}")

    def _handle_execution_error(self, msg: SubtaskErrorMessage, sender: ActorAddress) -> None:
        """Handle execution error from execution_actor"""
        task_id = msg.task_id
        if task_id in self._pending_execution_requests:
            original_sender = self._pending_execution_requests.pop(task_id)["original_sender"]
            self.send(original_sender, msg)
            self._report_event("failed", task_id, {"error": msg.error})
        else:
            logging.warning(f"Orphaned execution error for task: {task_id}")
    
    def _execute_intermediate(self, parent_task_id: str, context: Dict, original_sender: ActorAddress):
        """执行中间任务，协调子任务"""
        # 使用任务路由器选择最佳执行节点
        select_node_id = self._task_router.select_best_actor(self.agent_id, context)
        pending = set()
        
        if not select_node_id:
            logging.warning(f"Warning: No suitable child agent found for task {parent_task_id}")
            # 创建备用任务
            mcp_actor = self.createActor("McpLlmActor")
            self.send(mcp_actor, McpFallbackRequest(
                task_id=parent_task_id,
                context=context
            ))
            pending.add("MCP_FALLBACK_TASK")
        else:
            # 使用并行执行管理器生成和执行子任务
            plan = self._task_coordinator.plan_subtasks(select_node_id, context)
            
            # 使用并行执行管理器并行执行子任务
            child_tasks = []
            for i, step in enumerate(plan):
                child_cap = step["node_id"]
                child_ctx = self._task_coordinator.resolve_context({**context, **step.get("intent_params", {})}, self.agent_id)
                child_task_id = f"{parent_task_id}.child_{i}"
                
                # 创建子任务定义
                child_tasks.append({
                    "task_id": child_task_id,
                    "agent_id": step["node_id"],
                    "context": child_ctx,
                    "capability": child_cap
                })
            
            # 使用并行执行管理器执行所有子任务
            self._parallel_execution_manager.execute_subtasks(
                parent_task_id=parent_task_id,
                child_tasks=child_tasks,
                callback=self._on_subtask_completed
            )
            
            # 更新聚合状态
            pending = {task["task_id"] for task in child_tasks}
        
        self._aggregation_state[parent_task_id] = {
            "pending": pending,
            "results": {},
            "sender": original_sender
        }
    
    def _on_subtask_completed(self, task_id: str, result: Any, is_error: bool = False):
        """子任务完成回调"""
        if is_error:
            self._handle_subtask_error(task_id, result, None)  # 简化处理
        else:
            self._handle_subtask_completion(task_id, result, None)  # 简化处理
    
    def _handle_subtask_completion(self, task_id: str, result: Any, sender: ActorAddress):
        """处理子任务完成"""
        self._report_event("finished", task_id, {"result_preview": str(result)[:200]})
        self._complete_or_aggregate(task_id, result)
    
    def _handle_subtask_error(self, task_id: str, error: str, sender: ActorAddress):
        """处理子任务错误"""
        self._report_event("failed", task_id, {"error": str(error)[:200]})
        self._complete_or_aggregate(task_id, error, is_error=True)
    
    def _complete_or_aggregate(self, task_id: str, result_or_error: Any, is_error: bool = False):
        """完成或聚合任务结果"""
        parent_id = self._get_parent_task_id(task_id)
        
        # 如果是顶层任务
        if parent_id not in self._aggregation_state:
            # 检查是否是独立任务
            if task_id in self._aggregation_state:
                state = self._aggregation_state[task_id]
                self.send(state["sender"], SubtaskResultMessage(task_id, result_or_error))
                del self._aggregation_state[task_id]
            return
        
        # 处理子任务结果
        state = self._aggregation_state[parent_id]
        if is_error:
            # 任一子任务失败即整个任务失败
            del self._aggregation_state[parent_id]
            self.send(state["sender"], SubtaskErrorMessage(parent_id, f"Subtask {task_id} failed: {result_or_error}"))
            return
        
        state["results"][task_id] = result_or_error
        state["pending"].discard(task_id)
        
        # 所有子任务完成，聚合结果
        if not state["pending"]:
            final_result = ResultAggregator.aggregate_sequential(state["results"])
            self.send(state["sender"], SubtaskResultMessage(parent_id, final_result))
            del self._aggregation_state[parent_id]
    
    def _get_parent_task_id(self, task_id: str) -> str:
        """获取父任务ID"""
        return task_id.rsplit(".", 1)[0] if "." in task_id else ""
    
    def _get_or_create_actor_ref(self, agent_id: str) -> ActorAddress:
        """获取或创建智能体引用"""
        if agent_id not in self._actor_ref_cache:
            ref = self.createActor(AgentActor)
            # 构造初始化消息
            agent_info = self.registry.get_agent_meta(agent_id)
            if not agent_info:
                raise ValueError(f"Cannot create actor for unknown agent: {agent_id}")
            
            init_msg = InitMessage(
                agent_id=agent_id,
                capabilities=agent_info["capability"],
                memory_key=agent_id,
                registry=self.registry
            )
            self.send(ref, init_msg)
            self._actor_ref_cache[agent_id] = ref
        return self._actor_ref_cache[agent_id]
    
    def _report_event(self, event_type: str, task_id: str, details: Dict):
        """报告事件到EventBus和orchestrator"""
        # 映射事件类型到EventType枚举
        event_type_map = {
            "started": EventType.TASK_STARTED,
            "finished": EventType.SUBTASK_COMPLETED,
            "failed": EventType.CAPABILITY_FAILED
        }
        mapped_event_type = event_type_map.get(event_type, event_type)
        mapped_event_type = mapped_event_type.value if hasattr(mapped_event_type, 'value') else mapped_event_type
        
        # 发布事件到EventBus
        event_data = {**details, **{
            "task_id": task_id,
            "agent_id": self.agent_id,
            "event_type": event_type
        }}
        event_bus.publish_event(
            event_type=mapped_event_type,
            source=self.agent_id,
            data=event_data
        )
        
        # 保留原有功能 - 报告到orchestrator
        if self.orchestrator:
            self.orchestrator.report_event(event_type, task_id, details)
    
    def createActor(self, actorClass, *args, **kw):
        """创建智能体实例（具体实现由Thespian框架提供）"""
        # 这里只是接口定义，实际实现由Thespian提供
        pass
    
    def send(self, target, message):
        """发送消息给目标智能体（具体实现由Thespian框架提供）"""
        # 这里只是接口定义，实际实现由Thespian提供
        pass

# 导入Neo4j结构管理器相关的模块
from new.common.config.config_manager import config_manager
from new.external.agent_structure.structure_factory import create_agent_structure


class InitMessage:
    """初始化AgentActor的消息类"""
    def __init__(self, agent_id: str, agent_name: str, max_concurrency: int):
        self.agent_id = agent_id
        self.agent_name = agent_name
        self.max_concurrency = max_concurrency


    def receiveMessage(self, msg, sender):
        """处理接收到的消息"""
        if isinstance(msg, InitMessage):
            # 处理初始化消息
            self.agent_id = msg.agent_id
            self.agent_name = msg.agent_name
            self.max_concurrency = msg.max_concurrency
            
            # 初始化并行执行管理器
            self._parallel_execution_manager = ParallelExecutionManager()
            self.parallel_executor = self._parallel_execution_manager
            
            # 初始化任务协调器
            self._task_coordinator = TaskCoordinator()
            self.task_coordinator = self._task_coordinator
            
            # 初始化树管理器
            structure_manager = None
            try:
                structure_config = config_manager.get("agent_structure") or {"type": "neo4j"}
                structure_manager = create_agent_structure(structure_config)
                self._tree_manager = TreeManager(structure_manager)
                self.tree_manager = self._tree_manager
            except Exception as e:
                logging.error(f"Failed to initialize TreeManager: {str(e)}")
                # 如果无法使用Neo4j结构，则使用默认的TreeManager
                self._tree_manager = TreeManager()
                self.tree_manager = self._tree_manager
            finally:
                if structure_manager is not None:
                    structure_manager.close()
                    logging.debug(f"Structure manager for agent {self.agent_id} closed")
            
            logging.info(f"Agent {self.agent_id} ({self.agent_name}) initialized with max concurrency: {self.max_concurrency}")
        elif isinstance(msg, str) and msg == "TEST":
            # 测试消息处理
            logging.info(f"TEST message received for agent {self.agent_id}")
        else:
            # 调用原有消息处理逻辑
            # super().receiveMessage(msg, sender)  # 注意：如果父类没有默认实现，需要移除这行
            pass  # 保留原有处理逻辑占位符


# 恢复原有AgentActor类的其他方法
# ... existing AgentActor methods ...


def create_agent_actor(creator, agent_id: str, agent_name: str, max_concurrency: int):
    """创建并初始化AgentActor的工厂函数
    
    Args:
        creator: 可以是ActorSystem实例或Actor实例
                 - 如果是ActorSystem，创建顶级Actor
                 - 如果是Actor，创建子Actor
        agent_id: Agent唯一标识符
        agent_name: Agent名称
        max_concurrency: 最大并发数
    
    Returns:
        ActorRef: 创建的AgentActor引用
    """
    # 从Neo4j树结构中获取agent信息（可选）
    agent_info = None
    structure_manager = None
    
    try:
        # 创建结构管理器实例
        structure_config = config_manager.get("agent_structure") or {"type": "neo4j"}
        structure_manager = create_agent_structure(structure_config)
        
        # 从Neo4j获取agent信息
        agent_info = structure_manager.get_agent_by_id(agent_id)
        if agent_info:
            logging.info(f"Retrieved agent information from Neo4j: {agent_info}")
            # 更新agent_name和max_concurrency（如果Neo4j中有相关信息）
            agent_name = agent_info.get('meta', {}).get('name', agent_name)
            max_concurrency = agent_info.get('meta', {}).get('max_concurrency', max_concurrency)
    except Exception as e:
        logging.error(f"Failed to retrieve agent information from Neo4j: {str(e)}")
        # 忽略错误，使用默认参数继续创建
    finally:
        # 关闭结构管理器
        if structure_manager is not None:
            structure_manager.close()
            logging.debug(f"Structure manager for agent {agent_id} closed")
    
    # 创建AgentActor实例
    agent_actor_ref = creator.createActor(AgentActor)
    
    # 发送初始化消息
    init_msg = InitMessage(agent_id, agent_name, max_concurrency)
    
    # 根据creator类型选择tell方法
    if hasattr(creator, 'tell'):
        # 如果creator是ActorSystem
        creator.tell(agent_actor_ref, init_msg)
    else:
        # 如果creator是Actor
        creator.send(agent_actor_ref, init_msg)
    
    logging.info(f"Agent {agent_id} ({agent_name}) created with max concurrency: {max_concurrency}")
    return agent_actor_ref
