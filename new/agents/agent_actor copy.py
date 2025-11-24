"""Agent Actor - 智能体执行器
负责处理任务分发、子任务协调
"""
import logging
from typing import Any, Dict, Set, Optional
from thespian.actors import Actor, ActorAddress

from new.agents.coordination.task_coordinator import TaskCoordinator
from new.capabilities.routing.task_router import TaskRouter
from new.capabilities.result_aggregation.result_aggregation import ResultAggregator
from new.agents.tree.tree_manager import TreeManager
from new.events.event_bus import event_bus
from new.events.event_types import EventType
from new.common.messages.task_messages import TaskGroupRequest, TaskSpec

# 从common.messages导入所需的消息类
from new.common.messages import (
    InitMessage,
    AgentTaskMessage as TaskMessage,
    SubtaskResultMessage,
    SubtaskErrorMessage,
    MemoryResponseMessage,
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
        elif hasattr(message, 'group_id') and hasattr(message, 'results') and hasattr(message, 'failures'):
            # 处理来自TaskGroupAggregatorActor的结果
            self._handle_task_group_result(message, sender)
        elif isinstance(message, SubtaskResultMessage):
            self._handle_execution_result(message, sender)
        elif isinstance(message, SubtaskErrorMessage):
            self._handle_execution_error(message, sender)
        elif isinstance(message, dict) and message.get('type') == 'memory_response':
            # 处理来自memory_actor的字典格式响应
            self._handle_memory_dict_response(message, sender)
        elif isinstance(message, dict):
            # 处理字典类型的消息，包括来自TaskPlanningActor的响应
            self.receiveMsg_Dict(message, sender)
        else:
            self.logger.warning(f"Unknown message type: {type(message)}")
            
    def receiveMsg_Dict(self, message: Dict[str, Any], sender: ActorAddress):
        """
        处理字典类型的消息，包括来自TaskPlanningActor的响应
        """
        msg_type = message.get('type')
        
        # 处理任务规划完成的消息
        if msg_type == 'task_group_created':
            try:
                parent_task_id = message['parent_task_id']
                task_count = message['task_count']
                aggregator = message['aggregator']
                
                # 更新聚合状态
                if parent_task_id in self._aggregation_state:
                    # 这里可以更新聚合状态，添加更多信息
                    pass
                
                # 报告事件
                self._report_event("task_group_created", parent_task_id, {
                    "task_count": task_count,
                    "aggregator": aggregator
                })
                
                self.logger.info(f"接收到任务组创建通知，父任务ID: {parent_task_id}, 子任务数量: {task_count}")
                
            except Exception as e:
                self.logger.error(f"处理任务组创建通知时出错: {e}", exc_info=True)
        
        # 处理任务规划失败的消息
        elif msg_type == 'task_planning_error':
            try:
                parent_task_id = message['parent_task_id']
                error_msg = message['error']
                
                # 处理规划错误，可以发送错误响应给原始请求者
                if parent_task_id in self._aggregation_state:
                    original_sender = self._aggregation_state[parent_task_id]['sender']
                    # 可以向原始发送者发送错误消息
                    self.logger.error(f"任务规划失败: {parent_task_id}, 错误: {error_msg}")
                
                # 从聚合状态中移除失败的任务
                if parent_task_id in self._aggregation_state:
                    del self._aggregation_state[parent_task_id]
                    
            except Exception as e:
                self.logger.error(f"处理任务规划错误通知时出错: {e}", exc_info=True)
        
        # 其他字典类型消息的处理
        else:
            self.logger.warning(f"收到未知类型的字典消息: {msg_type}")
    
    def _initialize(self, msg: InitMessage, sender: ActorAddress):
        """初始化智能体"""
        self.agent_id = msg.agent_id
        self.capabilities = msg.capabilities
        self.registry = msg.registry
        
        # 创建数据actor实例
        self._data_actor = self.createActor(DataActor)
        
        # 创建记忆actor实例
        from new.capability_actors.memory_actor import MemoryActor
        self._memory_actor = self.createActor(MemoryActor)
        
        # 初始化记忆actor
        memory_init_msg = {
            "type": "initialize",
            "agent_id": self.agent_id
        }
        self.send(self._memory_actor, memory_init_msg)
        
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
        self.orchestrator = None
        
        # 初始化待处理的记忆请求字典
        self._pending_memory_requests = {}
        
        # 初始化logger
        self.logger = logging.getLogger(f"AgentActor_{self.agent_id}")
        
        self.logger.info(f"Agent {self.agent_id} initialized with capabilities: {self.capabilities}")
        self.logger.info(f"Created data_actor: {self._data_actor}")
        self.logger.info(f"Created memory_actor: {self._memory_actor}")
        
        # 向sender返回初始化完成的响应
        self.send(sender, "initialized")
    
    
    def _handle_task(self, task_msg: TaskMessage, sender: ActorAddress):
        """处理接收到的任务 - 先获取上下文记忆，再决定处理方式"""
        task_id = task_msg.task_id
        context = task_msg.context
        
        self._report_event("started", task_id, {"context_preview": str(context)[:200]})
        
        # 构造上下文记忆的键
        context_memory_key = f"task_context_{self.agent_id}_{task_id}"
        
        # 保存任务信息，等待记忆响应
        self._pending_memory_requests[task_id] = {
            "context": context,
            "sender": sender,
            "task_type": "context_retrieval"
        }
        
        # 如果存在记忆actor，发送检索请求
        # 向memory_actor发送短期记忆检索请求
        if hasattr(self, '_memory_actor') and self._memory_actor:
            try:
                # 向memory_actor发送短期记忆检索请求（优先级最高）
                memory_request = {
                    'type': 'retrieve_short_term_memory',
                    'task_id': task_id,
                    'query': str(context)[:500] if context else '',
                    'max_results': 5
                }
                self.send(self._memory_actor, memory_request)
                self.logger.info(f"发送短期记忆检索请求，任务ID: {task_id}")
                
                # 向memory_actor发送上下文记忆检索请求
                retrieve_request = {
                    "type": "retrieve",
                    "key": context_memory_key,
                    "memory_type": "short_term"
                }
                self.send(self._memory_actor, retrieve_request)
                self.logger.info(f"发送上下文记忆检索请求，任务ID: {task_id}")
                
                # 添加额外的长期记忆检索
                long_term_request = {
                    "type": "retrieve",
                    "key": f"agent_knowledge_{self.agent_id}",
                    "memory_type": "long_term",
                    "query": str(context)[:200] if context else ''
                }
                self.send(self._memory_actor, long_term_request)
                self.logger.info(f"发送长期记忆检索请求，任务ID: {task_id}")
                
            except Exception as e:
                self.logger.error(f"发送记忆检索请求失败: {e}")
                # 出错时，继续处理任务但不使用记忆
                self._process_task_after_memory(task_id, context, {}, sender)
        else:
            # 没有记忆actor时，直接处理任务
            self.logger.warning("记忆actor未初始化，直接处理任务")
            self._process_task_after_memory(task_id, context, {}, sender)
    
    def _process_task_after_memory(self, task_id: str, context: Dict, memory: Dict, sender: ActorAddress):
        """获取记忆后处理任务的方法"""
        # 将记忆合并到上下文中
        if not isinstance(context, dict):
            context = {}
        
        if memory:
            context['context_memory'] = memory
            self.logger.info(f"任务 {task_id} 已获取上下文记忆")
        
        # 判断任务类型并处理
        if self._is_leaf_task(context):
            # 叶子任务：直接执行
            self._execute_leaf_task(task_id, context, memory, sender)
        else:
            # 中间任务：创建子任务并协调执行
            self._execute_intermediate(task_id, context, sender)
    
    def _is_leaf_task(self, context: Dict) -> bool:
        """判断是否为叶子任务"""
        # 通过树结构管理来判断当前agent是否为叶子节点
        return self._tree_manager.is_leaf_agent(self.agent_id)
    
    def _execute_leaf_task(self, task_id: str, context: Dict, memory: Dict, sender: ActorAddress, capability: str = "dify_workflow"):
        """执行叶子任务 - 整合记忆信息并考虑已知参数"""
        # 确保context是字典类型
        if not isinstance(context, dict):
            context = {}
        
        # 记录任务开始
        self._report_event("leaf_task_started", task_id, {"capability": capability})
        
        # 使用记忆信息补充上下文
        enriched_context = self._enrich_context_with_memory(context, memory)
        
        # 检查是否有已知参数，如果没有，从记忆中查找
        known_params = self._extract_known_params(enriched_context)
        
        # 构建最终执行上下文
        final_context = {
            **enriched_context,
            'known_params': known_params
        }
        
        self.logger.info(f"执行叶子任务 {task_id}，使用记忆补充: {bool(memory)}")
        
        # 从tree_manager获取预定义的类型（会预先设定好）
        agent_meta = self._tree_manager.get_agent_meta(self.agent_id)
        execution_type = agent_meta.get("execution_type", "default") if agent_meta else "default"
        
        # 构造执行请求，将从tree_manager获取的类型传递给execution_actor
        execution_request = {
            "type": "leaf_task",
            "task_id": task_id,
            "context": final_context,
            "memory": memory,
            "capability": capability,
            "agent_id": self.agent_id,
            "execution_type": execution_type  # 添加执行类型字段
        }
        
        # 保存执行请求信息，以便在执行完成后处理响应
        self._pending_execution_requests[task_id] = {
            "original_sender": sender
        }
        
        # 使用通用的执行actor（惰性初始化）
        if not hasattr(self, '_execution_actor') or self._execution_actor is None:
            from new.capability_actors.execution_actor import ExecutionActor
            self._execution_actor = self.createActor(ExecutionActor)
        execution_actor = self._execution_actor
        
        # 发送执行请求给选定的执行actor
        try:
            self.send(execution_actor, execution_request)
            self._report_event("execution_request_sent", task_id, {
                "capability": capability,
                "executor": execution_actor.actor_id or "default_execution_actor"
            })
        except Exception as e:
            # 处理执行异常
            import logging
            error_msg = f"发送执行请求失败: {str(e)}"
            logging.error(error_msg)
            from new.common.messages import SubtaskErrorMessage
            error_msg_obj = SubtaskErrorMessage(task_id, error_msg)
            self.send(sender, error_msg_obj)
            
            # 记录任务失败
            self._report_event("leaf_task_failed", task_id, {"error": error_msg})
    
    def _enrich_context_with_memory(self, context: Dict, memory: Dict) -> Dict:
        """使用记忆信息丰富上下文"""
        enriched = context.copy()
        
        # 如果有记忆信息，整合到上下文中
        if memory:
            # 将记忆中的相关信息添加到上下文中
            if isinstance(memory, dict):
                # 如果memory中包含user_pref
                if 'user_pref' in memory:
                    enriched['user_preferences'] = memory['user_pref']
                # 如果memory中包含其他有用信息
                for key, value in memory.items():
                    if key not in enriched and key not in ['user_pref']:
                        enriched[f'memory_{key}'] = value
        
        return enriched
    
    def _extract_known_params(self, context: Dict) -> Dict:
        """从上下文中提取已知参数"""
        known_params = {}
        
        # 检查context中的常见参数位置
        potential_param_sources = ['params', 'parameters', 'args', 'arguments', 'input']
        
        for source in potential_param_sources:
            if source in context and isinstance(context[source], dict):
                known_params.update(context[source])
        
        # 直接从context中提取基本类型参数
        for key, value in context.items():
            if key not in ['capability', 'context_memory', 'user_preferences'] and \
               isinstance(value, (str, int, float, bool, list, dict)) and \
               not hasattr(value, '__dict__'):  # 排除对象引用
                known_params[key] = value
        
        return known_params
    

    def _handle_memory_response(self, key: str, memory_value: Any, sender: ActorAddress):
        """处理记忆响应"""
        if not self._pending_memory_requests:
            return
        
        task_id, task_info = next(iter(self._pending_memory_requests.items()))
        del self._pending_memory_requests[task_id]
        
        memory = {"user_pref": memory_value} if memory_value else {}
        
        # 处理任务
        self._process_task_after_memory(task_id, task_info["context"], memory, task_info["sender"])
        
    def _handle_memory_dict_response(self, message: Dict[str, Any], sender: ActorAddress):
        """处理来自memory_actor的字典格式记忆响应"""
        import time
        
        key = message.get('key')
        memory_value = message.get('value')
        memory_type = message.get('memory_type', 'short_term')
        
        # 查找相关的任务ID
        task_id = None
        task_info = None
        
        # 尝试通过键模式匹配找到对应的任务信息
        for tid, info in list(self._pending_memory_requests.items()):  # 使用list创建副本，避免迭代时修改
            # 匹配上下文检索类型的任务
            if info.get('task_type') == 'context_retrieval' and f"task_context_{self.agent_id}_{tid}" == key:
                task_id = tid
                task_info = info
                break
            # 匹配节点选择类型的任务
            elif info.get('task_type') == 'node_selection' and f"node_selection_history_{self.agent_id}" == key:
                task_id = tid
                task_info = info
                break
            # 兜底匹配
            elif f"_{tid}" in key:
                task_id = tid
                task_info = info
                break
        
        if not task_id or not task_info:
            self.logger.warning(f"收到未知键的记忆响应: {key}")
            return
            
        try:
            # 从待处理请求中移除该任务
            del self._pending_memory_requests[task_id]
            
            # 构建记忆数据结构
            if isinstance(memory_value, dict):
                memory = memory_value
            elif memory_value:
                memory = {"data": memory_value}
            else:
                memory = {}
            
            # 根据任务类型执行不同的后续处理
            task_type = task_info.get('task_type')
            
            if task_type == 'context_retrieval':
                # 上下文检索：继续处理任务
                self.logger.info(f"收到任务 {task_id} 的上下文记忆响应")
                self._process_task_after_memory(task_id, task_info["context"], memory, task_info["sender"])
                
                # 记录记忆使用情况
                self._report_event("memory_retrieved", task_id, {
                    "has_memory": bool(memory),
                    "memory_type": memory_type
                })
                
            elif task_type == 'node_selection':
                # 节点选择：继续创建任务规划器
                self.logger.info(f"收到任务 {task_id} 的节点选择历史")
                
                # 将节点选择历史合并到上下文中
                enhanced_context = task_info["context"].copy()
                if memory:
                    enhanced_context['node_selection_history'] = memory
                
                # 调用创建任务规划器的方法
                selected_node_id = task_info.get('selected_node_id')
                original_sender = task_info.get('sender')
                
                if selected_node_id and original_sender:
                    self._create_task_planner(
                        task_id, 
                        enhanced_context, 
                        original_sender, 
                        selected_node_id
                    )
                else:
                    self.logger.error(f"节点选择任务信息不完整: {task_info}")
                    
            else:
                # 未知任务类型，默认处理
                self.logger.warning(f"未知的记忆请求类型: {task_type}")
                self._process_task_after_memory(task_id, task_info["context"], memory, task_info.get("sender"))
                
        except Exception as e:
            self.logger.error(f"处理记忆响应时出错: {e}")
            # 出错时，尽量继续处理任务
            if 'sender' in task_info and 'context' in task_info:
                self._process_task_after_memory(task_id, task_info["context"], {}, task_info["sender"])
    
  

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
        """执行中间任务 - 添加记忆传递和节点选择历史获取"""
        self._report_event("intermediate_task_started", parent_task_id, {})
        
        # 使用任务路由器选择最佳执行节点
        select_node_id = self._task_router.select_best_actor(self.agent_id, context)
        
        if not select_node_id:
            logging.warning(f"Warning: No suitable child agent found for task {parent_task_id}")
            # 创建备用任务
            mcp_actor = self.createActor("McpLlmActor")
            self.send(mcp_actor, McpFallbackRequest(
                task_id=parent_task_id,
                context=context
            ))
            
            # 更新聚合状态
            self._aggregation_state[parent_task_id] = {
                "pending": {"MCP_FALLBACK_TASK"},
                "results": {},
                "sender": original_sender
            }
        else:
            # 构造节点选择历史记忆的键
            node_selection_key = f"node_selection_history_{self.agent_id}"
            
            # 保存任务信息，等待记忆响应
            self._pending_memory_requests[parent_task_id] = {
                "context": context,
                "sender": original_sender,
                "task_type": "node_selection",
                "original_task_id": parent_task_id,
                "selected_node_id": select_node_id
            }
            
            # 向memory_actor发送长期记忆检索请求，获取节点选择历史
            retrieve_request = {
                "type": "retrieve",
                "key": node_selection_key,
                "memory_type": "long_term"
            }
            
            if hasattr(self, '_memory_actor') and self._memory_actor:
                try:
                    self.send(self._memory_actor, retrieve_request)
                    self.logger.info(f"为任务 {parent_task_id} 检索节点选择历史")
                except Exception as e:
                    self.logger.error(f"检索节点选择历史失败: {e}")
                    # 出错时，继续处理但不使用历史
                    self._create_task_planner(parent_task_id, context, original_sender, select_node_id)
            else:
                # 没有记忆actor时，直接创建任务规划器
                self.logger.warning("记忆actor未初始化，跳过节点选择历史获取")
                self._create_task_planner(parent_task_id, context, original_sender, select_node_id)
    
    def _create_task_planner(self, parent_task_id: str, context: Dict, original_sender: ActorAddress, select_node_id: str):
        """创建任务规划器并发送规划请求"""
        # 确保context是字典类型
        if not isinstance(context, dict):
            context = {}
        
        # 从上下文中提取记忆（如果有）
        context_memory = context.get('context_memory', {})
        
        # 创建任务规划协调Actor，将任务规划逻辑委托给它处理
        from new.agents.coordination.task_planning_actor import TaskPlanningActor
        task_planning_actor = self.createActor(TaskPlanningActor)
        
        # 构造任务规划请求，包含记忆信息
        planning_request = {
            "type": "plan_tasks",
            "parent_task_id": parent_task_id,
            "selected_node_id": select_node_id,
            "context": context,
            "original_sender": original_sender,
            "task_coordinator": self._task_coordinator,
            "task_group_aggregator_class": TaskGroupAggregatorActor,
            "map_capability_func": self._map_capability_to_task_type,
            "context_memory": context_memory  # 传递记忆信息
        }
        
        # 发送异步请求给任务规划Actor
        self.send(task_planning_actor, planning_request)
        self.logger.info(f"为任务 {parent_task_id} 发送规划请求，携带记忆信息")
        
        # 初始化聚合状态，等待来自TaskPlanningActor的报告
        self._aggregation_state[parent_task_id] = {
            "pending": {parent_task_id},
            "results": {},
            "sender": original_sender
        }
        
        # 导入TaskGroupAggregatorActor用于类型引用
        from new.capability_actors.task_group_aggregator_actor import TaskGroupAggregatorActor
        
        self._report_event("planning_requested", parent_task_id, {})
    

        

    
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
    
    def _handle_task_group_result(self, message: Any, sender: ActorAddress):
        """处理来自TaskGroupAggregatorActor的任务组结果"""
        group_id = message.group_id
        
        if group_id in self._aggregation_state:
            state = self._aggregation_state.pop(group_id)
            original_sender = state["sender"]
            
            # 检查是否有失败任务
            if message.failures:
                error_msg = f"Task group {group_id} failed with {len(message.failures)} failures"
                self.send(original_sender, SubtaskErrorMessage(group_id, error_msg))
                self._report_event("failed", group_id, {"error": error_msg, "failures": message.failures})
            else:
                # 使用ResultAggregator聚合结果
                aggregated_result = ResultAggregator.aggregate_sequential(message.results)
                self.send(original_sender, SubtaskResultMessage(group_id, aggregated_result))
                self._report_event("finished", group_id, {"result_preview": str(aggregated_result)[:200]})
        else:
            logging.warning(f"Orphaned task group result for group: {group_id}")
    
    def _report_event(self, event_type: str, task_id: str, details: Dict):
        """报告事件到EventBus和orchestrator"""
        # 映射事件类型到EventType枚举
        event_type_map = {
            "started": EventType.TASK_STARTED,
            "finished": EventType.SUBTASK_COMPLETED,
            "failed": EventType.CAPABILITY_FAILED,
            "task_group_created": EventType.TASK_STARTED
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
    

    

# 导入Neo4j结构管理器相关的模块
from new.common.config.config_manager import config_manager
from new.external.agent_structure.structure_factory import create_agent_structure




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
    # 注意：InitMessage需要agent_id、capabilities、memory_key和registry参数
    init_msg = InitMessage(agent_id=agent_id, capabilities=[], memory_key="", registry=None)
    
    # 根据creator类型选择tell方法
    if hasattr(creator, 'tell'):
        # 如果creator是ActorSystem
        creator.tell(agent_actor_ref, init_msg)
    else:
        # 如果creator是Actor
        creator.send(agent_actor_ref, init_msg)
    
    logging.info(f"Agent {agent_id} ({agent_name}) created with max concurrency: {max_concurrency}")
    return agent_actor_ref
