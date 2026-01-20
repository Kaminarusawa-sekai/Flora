import logging
from typing import Dict, Any, Optional
from thespian.actors import ActorAddress, Actor, ActorExitRequest, ChildActorExited
from common.messages.task_messages import (
    ExecuteTaskMessage, ExecutionResultMessage, TaskCompletedMessage,
    AgentTaskMessage, ResumeTaskMessage
)
from capabilities import get_capability
from capabilities.llm_memory.interface import IMemoryCapability
from events.event_bus import event_bus
from common.event.event_type import EventType
from common.noop_memory import NoopMemory
from external.repositories.task_state_repo import (
    get_task_state_repo, TaskStateRepository, TaskStatus, PausedLayer
)

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
        # 任务状态存储库
        self._state_repo: Optional[TaskStateRepository] = None
        # 根回调地址（TaskRouter），用于 NEED_INPUT 直接回报
        self._root_reply_to: Optional[ActorAddress] = None

    def _get_state_repo(self) -> TaskStateRepository:
        """懒加载获取状态存储库"""
        if self._state_repo is None:
            self._state_repo = get_task_state_repo()
        return self._state_repo

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
            elif isinstance(message, ResumeTaskMessage):
                self._handle_resume_task(message, sender)
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
        # 保存根回调地址（用于 NEED_INPUT 直接回报 TaskRouter）
        if task.root_reply_to:
            self._root_reply_to = task.root_reply_to

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

    def _build_dify_running_config(self, task: AgentTaskMessage, dify_api_key: str) -> Dict[str, Any]:
        """构建 Dify 执行配置"""
        running_config = {
            "api_key": dify_api_key,
            "inputs": task.parameters,
            "agent_id": self.agent_id,
            "user_id": self.current_user_id,
            "content": str(task.content or ""),
            "description": str(task.description or ""),
            # 传递上下文，用于 Connector 层的参数补全
            "global_context": task.global_context or {},
            "enriched_context": task.enriched_context or {},
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
            # 传递上下文，用于 Connector 层的参数补全
            "global_context": task.global_context or {},
            "enriched_context": task.enriched_context or {},
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

        # 根据状态选择发送目标
        if status == "NEED_INPUT" and self._root_reply_to:
            # NEED_INPUT 直接发送给 TaskRouter（跳过中间层）
            self.log.info(f"Task {task_id} needs input, sending directly to TaskRouter via root_reply_to")
            self.send(self._root_reply_to, task_completed_msg)
        else:
            # 其他状态发送给原始发送者（逐层回传）
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

            # 2. 保存当前上下文到 Redis，用于断点续传
            self._save_execution_state(task_id, missing_params=missing_params)

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

    def _save_execution_state(self, task_id: str, missing_params: list = None) -> None:
        """
        保存执行状态到 Redis，用于断点续传

        Args:
            task_id: 任务ID
            missing_params: 缺失的参数列表
        """
        try:
            original_spec = getattr(self, "original_spec", None)
            if not original_spec:
                self.log.warning(f"No original_spec to save for task {task_id}")
                return

            # 构建 leaf_state（LeafActor 特有的状态）
            leaf_state = {
                "agent_id": self.agent_id,
                "meta": self.meta,
                "dify_config": self.meta.get("dify", "") if self.meta else "",
                "http_config": self.meta.get("http", "") if self.meta else "",
                "args_config": self.meta.get("args", "") if self.meta else "",
            }

            # 序列化 enriched_context（处理 ContextEntry 对象）
            enriched_context = {}
            if hasattr(original_spec, 'enriched_context') and original_spec.enriched_context:
                for k, v in original_spec.enriched_context.items():
                    if hasattr(v, 'to_dict'):
                        enriched_context[k] = v.to_dict()
                    elif hasattr(v, 'model_dump'):
                        enriched_context[k] = v.model_dump()
                    elif hasattr(v, '__dict__'):
                        enriched_context[k] = v.__dict__
                    else:
                        enriched_context[k] = v

            # 使用 TaskStateRepository 保存状态
            state_repo = self._get_state_repo()
            state_repo.save_need_input_state(
                task_id=task_id,
                trace_id=original_spec.trace_id,
                task_path=original_spec.task_path,
                user_id=self.current_user_id or "",
                paused_at=PausedLayer.LEAF,
                paused_step=None,
                missing_params=missing_params or [],
                agent_id=self.agent_id,
                original_content=original_spec.content or "",
                original_description=original_spec.description or "",
                global_context=original_spec.global_context or {},
                enriched_context=enriched_context,
                parameters=original_spec.parameters or {},
                leaf_state=leaf_state
            )
            self.log.info(f"Saved execution state to Redis for task {task_id}")

        except Exception as e:
            self.log.error(f"Failed to save execution state for task {task_id}: {e}")

    def _load_execution_state(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        从 Redis 加载执行状态，用于断点续传

        Args:
            task_id: 任务ID

        Returns:
            Dict: 保存的状态数据，不存在返回 None
        """
        try:
            state_repo = self._get_state_repo()
            state = state_repo.get_state(task_id)
            if state:
                self.log.info(f"Loaded execution state from Redis for task {task_id}")
                return state.to_dict()
        except Exception as e:
            self.log.error(f"Failed to load execution state for task {task_id}: {e}")
        return None

    def _handle_resume_task(self, message: ResumeTaskMessage, sender: ActorAddress) -> None:
        """
        处理恢复任务消息

        Args:
            message: ResumeTaskMessage 包含 task_id 和补充的参数
            sender: 发送者
        """
        task_id = message.task_id
        new_parameters = message.parameters or {}
        user_id = message.user_id

        self.log.info(f"Handling resume task: {task_id}, new params: {list(new_parameters.keys())}")

        # 1. 从 Redis 加载保存的状态
        state_data = self._load_execution_state(task_id)
        if not state_data:
            self.log.error(f"No saved state found for task {task_id}")
            error_msg = TaskCompletedMessage(
                task_id=task_id,
                trace_id=message.trace_id,
                task_path=message.task_path,
                result={"error": f"No saved state found for task {task_id}"},
                status="ERROR",
                agent_id=self.agent_id or "unknown"
            )
            self.send(sender, error_msg)
            return

        # 2. 恢复上下文
        leaf_state = state_data.get("leaf_state", {})
        self.agent_id = leaf_state.get("agent_id", self.agent_id)
        self.meta = leaf_state.get("meta")
        self.current_user_id = user_id or state_data.get("user_id")

        # 确保初始化
        if not self.memory_cap:
            try:
                self.memory_cap = get_capability("llm_memory", expected_type=IMemoryCapability)
            except Exception as e:
                self.log.warning(f"llm_memory unavailable, using NoopMemory: {e}")
                self.memory_cap = NoopMemory()
            self.log = logging.getLogger(f"LeafActor_{self.agent_id}")

        # 3. 合并参数
        original_params = state_data.get("parameters", {})
        merged_params = {**original_params, **new_parameters}

        # 4. 记录 sender 用于回复
        self.task_id_to_sender[task_id] = sender

        # 5. 重新执行任务
        self._resume_execution(
            task_id=task_id,
            trace_id=state_data.get("trace_id", message.trace_id),
            task_path=state_data.get("task_path", message.task_path),
            content=state_data.get("original_content", ""),
            description=state_data.get("original_description", ""),
            global_context=state_data.get("global_context", {}),
            enriched_context=state_data.get("enriched_context", {}),
            parameters=merged_params,
            leaf_state=leaf_state,
            sender=sender
        )

    def _resume_execution(
        self,
        task_id: str,
        trace_id: str,
        task_path: str,
        content: str,
        description: str,
        global_context: Dict[str, Any],
        enriched_context: Dict[str, Any],
        parameters: Dict[str, Any],
        leaf_state: Dict[str, Any],
        sender: ActorAddress
    ) -> None:
        """
        恢复执行任务

        Args:
            task_id: 任务ID
            trace_id: 跟踪ID
            task_path: 任务路径
            content: 原始内容
            description: 原始描述
            global_context: 全局上下文
            enriched_context: 富上下文
            parameters: 合并后的参数
            leaf_state: LeafActor 特有状态
            sender: 发送者
        """
        from capability_actors.execution_actor import ExecutionActor
        exec_actor = self.createActor(ExecutionActor)

        # 从 leaf_state 获取配置
        dify_config = leaf_state.get("dify_config", "")
        http_config = leaf_state.get("http_config", "")
        args_config = leaf_state.get("args_config", "")

        # 判断使用哪种能力
        if http_config and http_config.strip():
            capability = "http"
            running_config = self._build_http_running_config_from_state(
                task_id, content, description, parameters,
                global_context, enriched_context,
                http_config, args_config
            )
        else:
            capability = "dify"
            running_config = self._build_dify_running_config_from_state(
                content, description, parameters, dify_config
            )

        # 构建执行请求消息
        exec_request = ExecuteTaskMessage(
            task_id=task_id,
            task_path=task_path,
            trace_id=trace_id,
            capability=capability,
            running_config=running_config,
            content=content,
            description=description,
            global_context=global_context,
            enriched_context=enriched_context,
            user_id=self.current_user_id,
            sender=str(self.myAddress),
            reply_to=self.myAddress
        )

        # 发布任务恢复事件
        event_bus.publish_task_event(
            task_id=task_id,
            event_type=EventType.TASK_RESUMED.value,
            trace_id=trace_id,
            task_path=task_path,
            source="LeafActor",
            agent_id=self.agent_id,
            user_id=self.current_user_id,
            data={"capability": capability, "resumed_params": list(parameters.keys())}
        )

        self.log.info(f"Resuming execution for task {task_id} with capability={capability}")
        self.send(exec_actor, exec_request)

    def _build_dify_running_config_from_state(
        self,
        content: str,
        description: str,
        parameters: Dict[str, Any],
        dify_api_key: str
    ) -> Dict[str, Any]:
        """从保存的状态构建 Dify 执行配置"""
        running_config = {
            "api_key": dify_api_key,
            "inputs": parameters,
            "agent_id": self.agent_id,
            "user_id": self.current_user_id,
            "content": content,
            "description": description,
        }
        try:
            from env import DIFY_API_KEY, DIFY_BASE_URL
            if DIFY_BASE_URL:
                running_config["base_url"] = DIFY_BASE_URL
            if not running_config.get("api_key") and DIFY_API_KEY:
                running_config["api_key"] = DIFY_API_KEY
        except Exception:
            pass
        return running_config

    def _build_http_running_config_from_state(
        self,
        task_id: str,
        content: str,
        description: str,
        parameters: Dict[str, Any],
        global_context: Dict[str, Any],
        enriched_context: Dict[str, Any],
        http_config: str,
        args_config: str
    ) -> Dict[str, Any]:
        """从保存的状态构建 HTTP 执行配置"""
        import json

        # 解析 http_config
        parts = http_config.strip().split(" ", 1)
        method = parts[0].upper() if parts else "GET"
        path = parts[1] if len(parts) > 1 else "/"

        # 解析 args_config
        args_list = []
        if args_config:
            try:
                args_list = json.loads(args_config) if isinstance(args_config, str) else args_config
            except json.JSONDecodeError:
                pass

        # 从环境变量获取 base_url
        base_url = ""
        try:
            from env import ERP_API_BASE_URL
            base_url = ERP_API_BASE_URL
        except Exception:
            pass

        url = f"{base_url.rstrip('/')}{path}" if base_url else path

        running_config = {
            "url": url,
            "method": method,
            "path": path,
            "args_schema": args_list,
            "agent_id": self.agent_id,
            "user_id": self.current_user_id,
            "content": content,
            "description": description,
            "inputs": parameters,
            "global_context": global_context,
            "enriched_context": enriched_context,
            "node_meta": {
                "capability": self.meta.get("capability", "") if self.meta else "",
                "datascope": self.meta.get("datascope", "") if self.meta else "",
                "database": self.meta.get("database", "") if self.meta else "",
            }
        }

        # 认证信息
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
