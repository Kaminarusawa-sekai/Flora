# capability_actors/task_group_aggregator_actor.py
from typing import Dict, Any, List, Optional
from thespian.actors import Actor, ActorExitRequest,ChildActorExited
import uuid
import time

from ..common.messages import (
    TaskGroupRequestMessage as TaskGroupRequest, 
    TaskCompletedMessage,
    ParallelTaskRequestMessage,
    MCPTaskRequestMessage,
    ResultAggregatorTaskRequestMessage
)
from ..common.messages.types import MessageType

from ..common.taskspec import TaskSpec
from ..common.context.context_entry import ContextEntry
import logging

# 导入事件总线
from ..events.event_bus import event_bus
from common.event.event_type import EventType

# 导入相关 Actor 类引用
from .parallel_task_aggregator_actor import ParallelTaskAggregatorActor
from .result_aggregator_actor import ResultAggregatorActor
from .mcp_actor import MCPCapabilityActor

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskGroupAggregatorActor(Actor):
    """
    任务组聚合器Actor (Workflow Orchestrator)
    
    核心职责：
    1. 串行编排：严格按 Step 顺序执行。
    2. 数据流转：自动将上一步结果注入 Context，供下一步使用。
    3. 动态路由：
       - is_parallel=True -> ParallelTaskAggregatorActor (生成多个方案/优化)
       - Type=AGENT -> ResultAggregatorActor (重试与监管)
       - Type=MCP -> MCPCapabilityActor (原子工具)
    """
    
    def __init__(self):
        super().__init__()
        # 流程控制
        self.request_msg: Optional[TaskGroupRequest] = None
        self.sorted_subtasks: List[TaskSpec] = []
        self.current_step_index: int = 0
        self.current_user_id=None
        # 数据上下文 - 统一上下文传播与富集方案
        self.step_results: Dict[str, Any] = {}  # step_id -> result
        self.global_context: Dict[str, Any] = {}  # 【不变】全局上下文
        self.enriched_context: Dict[str, ContextEntry] = {}  # 【动态】富上下文
        
        # 当前工作的 Worker (用于验证回复来源)
        self.current_worker: Optional[Actor] = None 

        self.source=None

        self._pending_tasks: Dict[str, Any] = {}
        
        # 保存任务 ID 信息
        self._task_id: Optional[str] = None
        self._trace_id: Optional[str] = None
        self._task_path: Optional[str] = None
        
    def receiveMessage(self, msg: Any, sender: Actor) -> None:
        if isinstance(msg, ActorExitRequest):
            # 可选：做清理工作
            logger.info("Received ActorExitRequest, shutting down.")
            return  # Thespian will destroy the actor automatically
        elif isinstance(msg, ChildActorExited):
            # 可选：处理子 Actor 退出
            logger.info(f"Child actor exited: {msg.childAddress}, reason: {msg.__dict__}")
            return
        try:
            # 1. 启动请求
            if isinstance(msg, TaskGroupRequest):
                self._start_workflow(msg, sender)

            # 2. 处理标准对象类型的完成消息 (来自 ResultAggregator 或 MCP)
            elif isinstance(msg, TaskCompletedMessage):
                # 检查 status 属性判断任务是否成功
                if msg.status in ["SUCCESS"]:
                    result_data = msg.result
                    self._handle_step_success(result_data, sender)
                elif msg.status in ["FAILED", "ERROR", "CANCELLED"]:
                    # 处理失败情况
                    self._handle_step_failure(msg, sender)
        
        except Exception as e:
            logger.error(f"Workflow system error: {e}", exc_info=True)
            self._fail_workflow(f"System Error: {str(e)}")

    def _get_merged_context(
        self,
        task_id: str,
        global_ctx: Optional[Dict[str, Any]]=None,
        enriched_ctx: Optional[Dict[str, Any]]=None
    ) -> Dict[str, Any]:
        """
        获取或构建合并后的上下文（global + enriched），并自动缓存。
        
        用于首次执行和重试时保持上下文一致性。
        """
        # 检查是否已缓存（例如重试场景）
        if task_id in self._pending_tasks:
            cached = self._pending_tasks[task_id].get("context")
            if cached is not None:
                return cached

        # 首次构建：合并 global + enriched（enriched 优先）
        base = global_ctx or {}
        enriched = enriched_ctx or {}
        merged = {**base, **enriched}

        # 缓存到任务信息中（供重试使用）
        if task_id in self._pending_tasks:
            self._pending_tasks[task_id]["context"] = merged
        else:
            # 安全兜底：即使未注册，也返回合并结果（不应发生）
            logger.warning(f"_get_merged_context called before task {task_id} was registered")

        return merged


    def _start_workflow(self, msg: TaskGroupRequest, sender: Actor) -> None:
        """启动工作流"""
        logger.info(f"Starting TaskGroup Workflow: {msg.task_id}")
        self.current_user_id=msg.user_id

        self.request_msg = msg
        # 初始化上下文 - 统一上下文传播与富集方案
        self.global_context = msg.global_context.copy() if msg.global_context else {}
        self.enriched_context = msg.enriched_context.copy() if msg.enriched_context else {}
        self.step_results = {}
        self.source=sender
        
        # 保存任务 ID 信息
        self._task_id = msg.task_id
        self._trace_id = msg.trace_id
        self._task_path = msg.add_task_path("task_group")
        
        # 发布工作流启动事件
        event_bus.publish_task_event(
            task_id=self._task_id,
            event_type=EventType.TASK_RUNNING.value,
            trace_id=self._trace_id,
            task_path=self._task_path,
            source="TaskGroupAggregatorActor",
            agent_id="task_group_aggregator",
            user_id=self.current_user_id,
            data={
                "step_count": len(msg.subtasks),
                "workflow_name": msg.description or "TaskGroupWorkflow"
            },
            enriched_context_snapshot=self.enriched_context.copy()
        )
        
        # 按 Step 排序
        self.sorted_subtasks = sorted(
            [TaskSpec(**t) if isinstance(t, dict) else t for t in msg.subtasks],
            key=lambda x: x.step
        )
        self.current_step_index = 0
        
        # 执行第一步
        self._execute_next_step()


    def _has_current_step(self) -> bool:
        """判断是否还有未执行的步骤"""
        return 0 <= self.current_step_index < len(self.sorted_subtasks)

    def _get_current_step(self) -> TaskSpec:
        """安全获取当前步骤的 TaskSpec"""
        if not self._has_current_step():
            raise IndexError("No current step available")
        return self.sorted_subtasks[self.current_step_index]
    


    def _execute_next_step(self) -> None:
        if not self._has_current_step():
            self._finish_workflow()
            return

        current_task: TaskSpec = self._get_current_step()
        logger.info(f"Executing Step {current_task.step}: '{current_task.description}' (type={current_task.type})")
        
        # 发布任务步骤执行事件
        event_bus.publish_task_event(
            task_id=self._task_id,
            event_type=EventType.TASK_RUNNING.value,
            trace_id=self._trace_id,
            task_path=self._task_path,
            source="TaskGroupAggregatorActor",
            agent_id="task_group_aggregator",
            user_id=self.current_user_id,
            data={
                "step": current_task.step,
                "step_description": current_task.description,
                "step_type": current_task.type,
                "is_parallel": current_task.is_parallel
            },
            enriched_context_snapshot=self.enriched_context.copy()
        )
       
        # 2. 路由分发
        if current_task.is_parallel:
            # === 路由 A: 多样性/优化并行 ===
            self._dispatch_to_parallel_optimizer(current_task)
        else:
            # === 路由 B: 标准串行 ===
            task_type = current_task.type.upper()
            
            if task_type == "AGENT":
                # Agent -> ResultAggregator (负责 ExecutionActor 的生命周期)
                self._dispatch_to_result_aggregator(current_task)
            
            elif task_type == "MCP":
                # MCP -> 直接调用
                self._dispatch_to_mcp_executor(current_task)
                
            else:
                # 默认回落到 MCP
                logger.warning(f"Unknown type {task_type}, defaulting to MCP.")
                self._dispatch_to_mcp_executor(current_task)

    def _dispatch_to_parallel_optimizer(self, task: TaskSpec) -> None:
        """
        分发给 ParallelTaskAggregatorActor
        场景：需要生成"几个方案"，或者进行参数优化
        """
        logger.info(f"--> Route: Parallel Optimizer for Step {task.step}")
        
        parallel_aggregator = self.createActor(ParallelTaskAggregatorActor)
        self.current_worker = parallel_aggregator
        

        
        msg = ParallelTaskRequestMessage(
            task_id=str(uuid.uuid4()),
            trace_id=self._trace_id,
            task_path=self._task_path,
            step=task.step,
            content=task.content or "",
            description=task.description or "",
            spec=task,  # 注意：Parallel 需要完整 spec
            reply_to=self.myAddress,
            user_id=self.current_user_id,
            global_context=self.global_context.copy(),
            enriched_context=self.enriched_context.copy(),
        )
        self.send(parallel_aggregator, msg)


    def _dispatch_to_result_aggregator(self, task: TaskSpec) -> None:
        """分发给 ResultAggregator (Agent 任务代理)"""
        logger.info(f"--> Route: ResultAggregator for Step {task.step} (Agent)")
        
        aggregator = self.createActor(ResultAggregatorActor)
        self.current_worker = aggregator
        
        # 发送 ResultAggregatorTaskRequestMessage - 统一上下文传播与富集方案
        msg = ResultAggregatorTaskRequestMessage(
            task_id=str(uuid.uuid4()),
            trace_id=self._trace_id,
            task_path=self._task_path,
            step=task.step,
            content=task.content or "",
            description=task.description or "",
            spec=task,
            reply_to=self.myAddress,
            user_id=self.current_user_id,
            global_context=self.global_context.copy(),
            enriched_context=self.enriched_context.copy(),
        )
        self.send(aggregator, msg)


    def _dispatch_to_mcp_executor(self, task: TaskSpec) -> None:
        """分发给 MCP Actor (工具调用)"""
        logger.info(f"--> Route: MCP Executor for Step {task.step}")
        
        mcp_worker = self.createActor(MCPCapabilityActor)
        self.current_worker = mcp_worker

        # 使用 MCPTaskRequestMessage 替代 ExecuteTaskMessage - 统一上下文传播与富集方案
        msg = MCPTaskRequestMessage(
            task_id=str(uuid.uuid4()),
            trace_id=self._trace_id,
            task_path=self._task_path,
            step=task.step,
            content=task.content or "",
            description=task.description or "",
            executor=task.executor,  # ← 关键：MCP 消息需要 executor 字段
            reply_to=self.myAddress,
            user_id=self.current_user_id,
            global_context=self.global_context.copy(),
            enriched_context=self.enriched_context.copy(),
        )
        self.send(mcp_worker, msg)



    def _handle_step_success(self, result: Any, sender: Actor) -> None:
        """通用步骤成功回调"""
        current_task = self._get_current_step()
        step = current_task.step
        logger.info(f"Step {step} succeeded.")

        # 发布任务步骤成功事件
        event_bus.publish_task_event(
            task_id=self._task_id,
            event_type=EventType.TASK_PROGRESS.value,
            trace_id=self._trace_id,
            task_path=self._task_path,
            source="TaskGroupAggregatorActor",
            agent_id="task_group_aggregator",
            user_id=self.current_user_id,
            data={
                "step": step,
                "step_description": current_task.description,
                "step_result": result,
                "completed_steps": self.current_step_index + 1,
                "total_steps": len(self.sorted_subtasks)
            },
            enriched_context_snapshot=self.enriched_context.copy()
        )

        # 存储结果
        step_key = f"step_{step}_output"
        # 1. 存储结果 (Specific Key)
        self.step_results[step_key] = result
        
        # 2. 上下文富集 - 统一上下文传播与富集方案
        # 2.1 存储到富上下文中
        # self.enriched_context[step_key] = result
        
        # 2.2 存储通用 key 用于隐式传递 (默认把上一步结果传给下一步)
        # self.enriched_context["prev_step_output"] = result
        
        # 2.3 添加上下文富集逻辑：从结果中提取有用信息
        # 生成安全键名，包含任务路径前缀
        task_path_key = f"{self._task_path.replace('/', '_')}.step_{current_task.step}"
        
        self._enrich_context_from_result(result, task_path_key,source=str(sender),task_path=self._task_path)
        
        # 3. 推进
        self.current_step_index += 1
        self._execute_next_step()

    def _enrich_context_from_result(self, result: Any, prefix: str, source: str = "tool_output", task_path: str = "") -> None:
        """
        将 result 整体作为 value 封装进 ContextEntry，存入 enriched_context[prefix]
        
        Args:
            result: 要保存的任意结果（支持 dict/list/str/int 等）
            prefix: 上下文中的键名（如 "profile"、"search_results"）
            source: 数据来源（默认 "tool_output"）
            task_path: 任务路径（用于追踪）
        """
        # 只有当 result 不是 None 时才记录（可选：也可保留 None）
        if result is None:
            return

        entry = ContextEntry(
            value=result,
            source=source,
            task_path=task_path,
            timestamp=time.time(),  # 或用 default_factory 自动填充
            confidence=1.0
        )
        self.enriched_context[prefix] = entry


    def _handle_step_failure(self, msg: TaskCompletedMessage, sender: Actor) -> None:
        """通用步骤失败回调"""
        if self._has_current_step():
            current_task = self._get_current_step()
            # 从 TaskCompletedMessage 中提取错误信息
            error_msg = f"Step {current_task} failed with status: {msg.status}"
            if hasattr(msg, 'error') and msg.error:
                error_msg += f": {msg.error}"
            elif hasattr(msg, 'result') and msg.result:
                # 如果 result 包含错误信息，也提取出来
                error_msg += f": {str(msg.result)}"
            logger.error(error_msg)
            self._fail_workflow(error_msg)
        else:
            logger.error("Workflow failed with no current step context.")
            self._fail_workflow("Workflow failed during finalization or invalid state.")

   

    def _build_comprehensive_prompt(self, prev_output: Any, description: str, current_instruction: str) -> str:
        """
        辅助方法：构建 LLM 友好的综合上下文 Prompt
        """
        prompt_parts = []
        
        # 1. 添加背景/上一步结果
        if prev_output:
            # 简单处理：如果是复杂对象转字符串，如果是长文本则直接拼接
            prev_str = str(prev_output)
            # 截断过长的输出防止 Context Window 爆炸 (可选，这里先不做)
            
            prompt_parts.append(f"### Previous Step Result / Context ###\n{prev_str}\n")
        
        # 2. 添加当前任务目标
        if description:
            prompt_parts.append(f"### Current Task Goal ###\n{description}\n")
        
        # 3. 添加具体指令
        if current_instruction:
            prompt_parts.append(f"### Instruction / Parameters ###\n{current_instruction}")
            
        return "\n".join(prompt_parts)

    def _finish_workflow(self) -> None:
        """完成"""
        logger.info(f"Workflow {self.request_msg.task_id} Completed.")
        
        # 发布工作流完成事件
        event_bus.publish_task_event(
            task_id=self._task_id,
            event_type=EventType.TASK_COMPLETED.value,
            trace_id=self._trace_id,
            task_path=self._task_path,
            source="TaskGroupAggregatorActor",
            agent_id="task_group_aggregator",
            user_id=self.current_user_id,
            data={
                "step_count": len(self.sorted_subtasks),
                "completed_steps": self.current_step_index,
                "workflow_result": {"step_results": self.step_results}
            },
            enriched_context_snapshot=self.enriched_context.copy()
        )
        
        # 构造最终结果，使用TaskCompletedMessage
        final_msg = TaskCompletedMessage(
            message_type=MessageType.TASK_COMPLETED,
            status="SUCCESS",
            result={"step_results": self.step_results},
            task_id=self._task_id,
            trace_id=self._trace_id,
            task_path=self._task_path,
            step=None,
        )
        
        target = self.source 
        self.send(target, final_msg)
        self.send(self.myAddress, ActorExitRequest())

    def _fail_workflow(self, error_msg: str) -> None:
        """失败"""
        logger.error(f"Workflow Terminated: {error_msg}")
        
        # 发布工作流失败事件
        event_bus.publish_task_event(
            task_id=self._task_id,
            event_type=EventType.TASK_FAILED.value,
            trace_id=self._trace_id,
            task_path=self._task_path,
            source="TaskGroupAggregatorActor",
            agent_id="task_group_aggregator",
            user_id=self.current_user_id,
            data={
                "step_count": len(self.sorted_subtasks),
                "completed_steps": self.current_step_index,
                "step_results": self.step_results
            },
            enriched_context_snapshot=self.enriched_context.copy(),
            error=error_msg
        )
        
        current_step = self._get_current_step().step if self._has_current_step() else None
        fail_msg = TaskCompletedMessage(
            message_type=MessageType.TASK_COMPLETED,
            status="FAILED",
            result={"error": error_msg, "step_results": self.step_results},
            task_id=self._task_id,
            trace_id=self._trace_id,
            task_path=self._task_path,
            step=current_step,
        )
        target = self.source
        self.send(target, fail_msg)
        self.send(self.myAddress, ActorExitRequest())