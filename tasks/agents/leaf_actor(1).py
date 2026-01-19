import logging
from typing import Dict, Any, Optional
from thespian.actors import ActorAddress, Actor, ActorExitRequest,ChildActorExited
from common.messages.task_messages import ExecuteTaskMessage, ExecutionResultMessage, TaskCompletedMessage, AgentTaskMessage
from capabilities import get_capability
from capabilities.llm_memory.interface import IMemoryCapability
from events.event_bus import event_bus
from common.event.event_type import EventType
from common.noop_memory import NoopMemory

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
            try:
                self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
            except Exception as e:
                self.log.warning(f"llm_memory unavailable, using NoopMemory: {e}")
                self.memory_cap = NoopMemory()
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
                try:
                    self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
                except Exception as e:
                    self.log.warning(f"llm_memory unavailable, using NoopMemory: {e}")
                    self.memory_cap = NoopMemory()
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
        from capability_actors.execution_actor import ExecutionActor
        exec_actor = self.createActor(ExecutionActor)

        # 根据 meta 中的 dify 和 http 属性判断使用哪种能力
        dify_config = self.meta.get("dify", "")
        http_config = self.meta.get("http", "")
        args_config = self.meta.get("args", "")

        # === 语义指针补全：消解代词歧义 ===
        # 在执行前，对参数描述进行语义指针补全
        semantic_pointers = self._resolve_semantic_pointers_for_task(task, args_config)
        if semantic_pointers:
            # 将语义指针存入 task 的 semantic_pointers 字段
            from common.context.context_entry import SemanticPointer
            for param_name, pointer_info in semantic_pointers.items():
                task.semantic_pointers[param_name] = SemanticPointer(
                    param_name=param_name,
                    original_desc=pointer_info.get("original_desc", ""),
                    resolved_desc=pointer_info.get("resolved_desc", ""),
                    confidence=pointer_info.get("confidence", 1.0),
                    resolution_chain=pointer_info.get("resolution_chain", []),
                    has_ambiguity=pointer_info.get("has_ambiguity", False)
                )

        # 判断使用哪种能力：优先 http（如果有值），否则用 dify
        if http_config and http_config.strip():
            capability = "http"
            running_config = self._build_http_running_config(task, http_config, args_config)
        else:
            capability = "dify"
            running_config = self._build_dify_running_config(task, dify_config)

        # 构建执行请求消息
        exec_request = ExecuteTaskMessage(
            task_id=task.task_id,
            task_path=task.task_path,
            trace_id=task.trace_id,
            capability=capability,
            running_config=running_config,
            content=task.content,
            description=task.description,
            global_context=task.global_context,
            enriched_context=task.enriched_context,
            semantic_pointers=task.semantic_pointers,  # 传递语义指针
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
            data={"node_id": self.agent_id, "type": "leaf_execution", "capability": capability}
        )

        self.send(exec_actor, exec_request)

    def _resolve_semantic_pointers_for_task(
        self,
        task: AgentTaskMessage,
        args_config: str
    ) -> Dict[str, Any]:
        """
        为任务参数进行语义指针补全。

        Args:
            task: 任务消息
            args_config: 参数配置 JSON 字符串

        Returns:
            Dict: 参数名 -> 语义指针信息
        """
        import json

        # 1. 从 args_config 中提取参数描述
        param_descriptions = {}
        if args_config:
            try:
                args_list = json.loads(args_config) if isinstance(args_config, str) else args_config
                if isinstance(args_list, list):
                    for arg in args_list:
                        if isinstance(arg, dict):
                            name = arg.get("name", "")
                            desc = arg.get("description", "") or arg.get("desc", "")
                            if name and desc:
                                param_descriptions[name] = desc
            except json.JSONDecodeError:
                self.log.warning(f"Failed to parse args_config for semantic pointers: {args_config}")

        if not param_descriptions:
            return {}

        # 2. 调用 TreeContextResolver 进行语义指针补全
        try:
            from capabilities.context_resolver.tree_context_resolver import TreeContextResolver
            from capabilities.context_resolver.interface import IContextResolverCapbility
            from capabilities import get_capability

            resolver = get_capability("tree_context_resolver", expected_type=IContextResolverCapbility)

            # 构建当前上下文
            current_context = {
                "content": task.content,
                "description": task.description,
                "global_context": task.global_context,
                "enriched_context": task.enriched_context
            }

            # 解析语义指针
            semantic_pointers = resolver.resolve_semantic_pointers(
                param_descriptions=param_descriptions,
                current_context=current_context,
                agent_id=self.agent_id,
                user_id=self.current_user_id or "default"
            )

            # 记录日志
            for param_name, pointer_info in semantic_pointers.items():
                if pointer_info.get("has_ambiguity"):
                    self.log.info(
                        f"[SemanticPointer] {param_name}: "
                        f"'{pointer_info.get('original_desc')}' -> "
                        f"'{pointer_info.get('resolved_desc')}' "
                        f"(confidence: {pointer_info.get('confidence', 0):.2f})"
                    )

            return semantic_pointers

        except Exception as e:
            self.log.warning(f"Failed to resolve semantic pointers: {e}")
            return {}

    def _build_dify_running_config(self, task: AgentTaskMessage, dify_api_key: str) -> Dict[str, Any]:
        """构建 Dify 执行配置"""
        running_config = {
            "api_key": dify_api_key,
            "inputs": task.parameters,
            "agent_id": self.agent_id,
            "user_id": self.current_user_id,
            "content": str(task.content or ""),
            "description": str(task.description or ""),
        }
        try:
            from env import DIFY_API_KEY, DIFY_BASE_URL
            if DIFY_BASE_URL and not running_config.get("base_url"):
                running_config["base_url"] = DIFY_BASE_URL
            api_key_val = running_config.get("api_key")
            if not isinstance(api_key_val, str) or not api_key_val:
                if DIFY_API_KEY:
                    running_config["api_key"] = DIFY_API_KEY
        except Exception:
            pass
        return running_config

    def _build_http_running_config(self, task: AgentTaskMessage, http_config: str, args_config: str) -> Dict[str, Any]:
        """
        构建 HTTP 执行配置

        Args:
            task: 任务消息
            http_config: HTTP 配置字符串，格式如 "POST /admin-api/erp/product/create"
            args_config: 参数配置 JSON 字符串
        """
        import json

        # 解析 http_config: "POST /admin-api/erp/product/create"
        parts = http_config.strip().split(" ", 1)
        method = parts[0].upper() if parts else "GET"
        path = parts[1] if len(parts) > 1 else "/"

        # 解析 args_config
        args_list = []
        if args_config:
            try:
                args_list = json.loads(args_config) if isinstance(args_config, str) else args_config
            except json.JSONDecodeError:
                self.log.warning(f"Failed to parse args_config: {args_config}")

        # 从环境变量获取 base_url
        base_url = ""
        try:
            from env import ERP_API_BASE_URL
            base_url = ERP_API_BASE_URL
        except Exception:
            pass

        # 构建完整 URL
        url = f"{base_url.rstrip('/')}{path}" if base_url else path

        # 将语义指针转换为可序列化的字典格式
        semantic_pointers_dict = {}
        if task.semantic_pointers:
            for param_name, pointer in task.semantic_pointers.items():
                if hasattr(pointer, 'model_dump'):
                    semantic_pointers_dict[param_name] = pointer.model_dump()
                elif hasattr(pointer, 'dict'):
                    semantic_pointers_dict[param_name] = pointer.dict()
                elif isinstance(pointer, dict):
                    semantic_pointers_dict[param_name] = pointer

        running_config = {
            "url": url,
            "method": method,
            "path": path,
            "args_schema": args_list,  # 参数 schema，用于参数校验和提取
            "agent_id": self.agent_id,
            "user_id": self.current_user_id,
            "content": str(task.content or ""),
            "description": str(task.description or ""),
            "inputs": task.parameters or {},
            # 关键：传递上下文，用于参数提取
            "global_context": task.global_context or {},
            "enriched_context": task.enriched_context or {},
            # 【新增】传递语义指针，用于增强参数描述
            "semantic_pointers": semantic_pointers_dict,
            # 传递节点元数据，便于 connector 使用
            "node_meta": {
                "capability": self.meta.get("capability", ""),
                "datascope": self.meta.get("datascope", ""),
                "database": self.meta.get("database", ""),
            }
        }

        # 尝试从环境变量获取认证信息
        try:
            from env import ERP_API_TOKEN
            if ERP_API_TOKEN:
                running_config["headers"] = {
                    "Authorization": f"Bearer {ERP_API_TOKEN}",
                    "Content-Type": "application/json"
                }
        except Exception:
            running_config["headers"] = {"Content-Type": "application/json"}

        return running_config

    def _handle_execution_result(self, result_msg: ExecutionResultMessage, sender: ActorAddress):
        """处理执行结果消息"""
        task_id = result_msg.task_id
        result_data = result_msg.result
        status = result_msg.status
        error = result_msg.error
        missing_params = result_msg.missing_params

        if status == "NEED_INPUT":
            if not isinstance(result_data, dict):
                result_data = {"message": result_data}
            if missing_params:
                result_data.setdefault("missing_params", missing_params)

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
        from capability_actors.execution_actor import ExecutionActor
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
