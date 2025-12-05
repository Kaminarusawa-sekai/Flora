# capability_actors/task_group_aggregator_actor.py
from typing import Dict, Any, List, Optional
from thespian.actors import Actor, ActorExitRequest
from common.messages.task_messages import (
    TaskGroupRequest, TaskCompleted, TaskFailed,
    ExecuteTaskMessage, TaskSpec, TaskGroupResult,
    RepeatTaskRequest, MCPTaskMessage
)
import logging

# 导入事件总线
from events.event_bus import event_bus
from events.event_types import EventType

# 导入相关 Actor 类引用
from capability_actors.parallel_task_aggregator_actor import ParallelTaskAggregatorActor
from capability_actors.result_aggregator_actor import ResultAggregatorActor
from capability_actors.mcp_actor import MCPCapabilityActor

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
        # 数据上下文
        self.step_results: Dict[str, Any] = {}  # step_id -> result
        self.context: Dict[str, Any] = {}       # 全局变量池
        
        # 当前工作的 Worker (用于验证回复来源)
        self.current_worker: Optional[Actor] = None 
        
    def receiveMessage(self, msg: Any, sender: Actor) -> None:
        try:
            # 1. 启动请求
            if isinstance(msg, TaskGroupRequest):
                self._start_workflow(msg, sender)
            
            # 2. 处理并行聚合器/优化的返回结果 (通常是字典)
            elif isinstance(msg, dict) and msg.get("type") in ["parallel_task_result", "optimization_result"]:
                self._handle_parallel_result(msg, sender)

            # 3. 处理标准对象类型的完成消息 (来自 ResultAggregator 或 MCP)
            elif isinstance(msg, (TaskCompleted, TaskGroupResult)):
                # 兼容处理：如果是 TaskGroupResult，通常包含 results 字典；TaskCompleted 包含 result
                # 这里假设 ResultAggregator 返回的是 TaskCompleted (单任务模式) 或 TaskGroupResult (多任务模式)
                result_data = None
                if isinstance(msg, TaskCompleted):
                    result_data = msg.result
                elif isinstance(msg, TaskGroupResult):
                    # 如果返回的是 GroupResult，我们取 results 里的值，或者整个 results
                    result_data = msg.results
                
                self._handle_step_success(result_data, sender)
                
            # 4. 处理失败
            elif isinstance(msg, TaskFailed):
                self._handle_step_failure(msg, sender)
            
            # 5. 处理字典类型的失败 (兼容并行聚合器的返回)
            elif isinstance(msg, dict) and msg.get("success") is False:
                # 构造一个 TaskFailed 对象方便统一处理
                failed_msg = TaskFailed(
                    task_id=msg.get("task_id", "unknown"),
                    error=msg.get("error", "Unknown parallel error"),
                    details=str(msg)
                )
                self._handle_step_failure(failed_msg, sender)
                
        except Exception as e:
            logger.error(f"Workflow system error: {e}", exc_info=True)
            self._fail_workflow(f"System Error: {str(e)}")

    def _start_workflow(self, msg: TaskGroupRequest, sender: Actor) -> None:
        """启动工作流"""
        logger.info(f"Starting TaskGroup Workflow: {msg.parent_task_id}")
        self.current_user_id=msg.user_id

        self.request_msg = msg
        self.context = msg.context.copy() if msg.context else {}
        self.step_results = {}
        
        # 按 Step 排序
        self.sorted_subtasks = sorted(msg.subtasks, key=lambda x: x.step)
        self.current_step_index = 0
        
        # 执行第一步
        self._execute_next_step()

    def _execute_next_step(self) -> None:
        """执行当前步骤"""
        if self.current_step_index >= len(self.sorted_subtasks):
            self._finish_workflow()
            return

        current_task = self.sorted_subtasks[self.current_step_index]
        logger.info(f"Executing Step {current_task.step}: {current_task.description}")

        # === 核心修改点 1: 传入整个 task 对象进行智能解析 ===
        # 解析依赖，构建综合上下文
        resolved_params = self._resolve_dependencies(current_task)

        # 2. 路由分发
        if current_task.is_parallel:
            # === 路由 A: 多样性/优化并行 ===
            self._dispatch_to_parallel_optimizer(current_task, resolved_params)
        else:
            # === 路由 B: 标准串行 ===
            task_type = current_task.type.upper()
            
            if task_type == "AGENT":
                # Agent -> ResultAggregator (负责 ExecutionActor 的生命周期)
                self._dispatch_to_result_aggregator(current_task, resolved_params)
            
            elif task_type == "MCP":
                # MCP -> 直接调用
                self._dispatch_to_mcp_executor(current_task, resolved_params)
                
            else:
                # 默认回落到 ResultAggregator
                logger.warning(f"Unknown type {task_type}, utilizing ResultAggregator.")
                self._dispatch_to_result_aggregator(current_task, resolved_params)

    def _dispatch_to_parallel_optimizer(self, task: TaskSpec, params: Dict[str, Any]) -> None:
        """
        分发给 ParallelTaskAggregatorActor
        场景：需要生成"几个方案"，或者进行参数优化
        """
        logger.info(f"--> Route: Parallel Optimizer for Step {task.step}")
        
        parallel_aggregator = self.createActor(ParallelTaskAggregatorActor)
        self.current_worker = parallel_aggregator
        
        # 1. 确定重复次数 (count)
        # 优先从 params 读取 (如 "generate_n": 3), 否则默认 3
        count = params.get("count", params.get("generate_n", 3))
        
        # 2. 准备 Spec
        # 我们需要克隆一个 Spec 并设置 repeat_count，因为 ParallelActor 依赖 spec.repeat_count
        # 注意：这里我们修改 spec 的 params 为解析后的 params
        task.params = params
        task.repeat_count = count 
        
        # 设置默认聚合策略，如果是创意生成，通常希望保留所有结果列表
        if not hasattr(task, 'aggregation_strategy') or not task.aggregation_strategy:
             # 动态添加属性或在 params 里设置，ParallelActor 会读取 spec.aggregation_strategy
             # 这里假设 TaskSpec 类有这个字段，或者通过 params 传递
             task.aggregation_strategy = "list" 

        # 3. 发送 RepeatTaskRequest
        request = RepeatTaskRequest(
            source=self.myAddress,
            destination=parallel_aggregator,
            spec=task,
            # ParallelActor 的 receiveMessage 主要看 spec，但也可能看 msg 属性
            # 这里保持冗余以防万一
            count=count,
            strategy=task.strategy_reasoning
        )
        self.send(parallel_aggregator, request)

    def _dispatch_to_result_aggregator(self, task: TaskSpec, params: Dict[str, Any]) -> None:
        """分发给 ResultAggregator (Agent 任务代理)"""
        logger.info(f"--> Route: ResultAggregator for Step {task.step} (Agent)")
        
        aggregator = self.createActor(ResultAggregatorActor)
        self.current_worker = aggregator
        
        # 1. 初始化
        self.send(aggregator, {
            "type": "initialize",
            "trace_id": f"{self.request_msg.parent_task_id}_step_{task.step}",
            "max_retries": 3,
            "timeout": 300
        })
        
        # 2. 发送单任务执行指令
        self.send(aggregator, {
            "type": "execute_subtask",
            "task_id": f"step_{task.step}",
            "task_spec": task,
            "capability": "AGENT",
            "executor": task.executor,
            "parameters": params,
            "description": task.description,
            "user_id": self.current_user_id,
        })

    def _dispatch_to_mcp_executor(self, task: TaskSpec, params: Dict[str, Any]) -> None:
        """分发给 MCP Actor (工具调用)"""
        logger.info(f"--> Route: MCP Executor for Step {task.step}")
        
        mcp_worker = self.createActor(MCPCapabilityActor)
        self.current_worker = mcp_worker

        # 使用 MCPTaskMessage 替代 ExecuteTaskMessage
        msg = MCPTaskMessage(
            step=task.step,
            description=task.description,  # 假设 TaskSpec 有 description 字段
            params=params,
            executor=task.executor if hasattr(task, 'executor') else None,  # 可选：如果 TaskSpec 有指定执行器
            source=self.myAddress,
            destination=mcp_worker,
            reply_to=self.myAddress  # 注意：MCPTaskMessage 没有 reply_to 字段！
        )
        self.send(mcp_worker, msg)

    def _handle_parallel_result(self, msg: Dict[str, Any], sender: Actor) -> None:
        """
        专门处理 ParallelTaskAggregator 返回的字典结果
        格式参考: {"type": "parallel_task_result", "success": True, "aggregated_result": ...}
        """
        if msg.get("success"):
            # 提取核心结果
            # 如果是 optimization_result，结果在 best_parameters
            # 如果是 parallel_task_result，结果在 aggregated_result
            result = msg.get("aggregated_result") or msg.get("best_parameters")
            
            logger.info(f"Parallel execution success. Result type: {type(result)}")
            self._handle_step_success(result, sender)
        else:
            # 失败处理
            error_msg = msg.get("error", "Parallel execution failed")
            failures = msg.get("failures", [])
            logger.error(f"Parallel execution failed: {error_msg}, Details: {failures}")
            
            self._fail_workflow(f"Parallel Task Failed: {error_msg}")

    def _handle_step_success(self, result: Any, sender: Actor) -> None:
        """通用步骤成功回调"""
        current_task = self.sorted_subtasks[self.current_step_index]
        step_key = f"step_{current_task.step}_output"
        
        logger.info(f"Step {current_task.step} completed successfully.")
        
        # 1. 存储结果 (Specific Key)
        self.step_results[step_key] = result
        self.context[step_key] = result
        
        # 2. 存储结果 (Generic Key for implicit chaining)
        # 这实现了 "默认把上一步结果传给下一步"
        self.context["prev_step_output"] = result
        
        # 3. 推进
        self.current_step_index += 1
        self._execute_next_step()

    def _handle_step_failure(self, msg: TaskFailed, sender: Actor) -> None:
        """通用步骤失败回调"""
        current_task = self.sorted_subtasks[self.current_step_index]
        error_msg = f"Step {current_task.step} failed: {msg.error}"
        logger.error(error_msg)
        self._fail_workflow(error_msg)

    def _resolve_dependencies(self, task: TaskSpec) -> Dict[str, Any]:
        """
        依赖解析与上下文构建
        
        逻辑：
        1. 获取上一步的输出 (prev_step_output)
        2. 获取当前任务的描述 (description)
        3. 获取当前参数 (params)
        4. 如果 params 是字符串，或者存在上一步结果，则构建一个"综合指导性文本"
        """
        prev_output = self.context.get("prev_step_output")
        raw_params = task.params
        
        # === 情况 A: 参数是字符串 (如 "时间范围：上个月") ===
        # 用户的意图是：把这段话 + 上一步的结果 合并成一个 Prompt 发给 Agent/MCP
        if isinstance(raw_params, str):
            # 构建综合上下文文本
            combined_prompt = self._build_comprehensive_prompt(
                prev_output=prev_output,
                description=task.description,
                current_instruction=raw_params
            )
            
            logger.info(f"Converted string params to comprehensive context for Step {task.step}")
            
            # 返回标准字典，使用通用 key (如 input/query) 适配下游 Actor
            return {
                "input": combined_prompt,
                "query": combined_prompt,  # 冗余字段以适配不同类型的 Tool
                "instruction": raw_params, # 保留原始指令
                "_is_context_expanded": True
            }

        # === 情况 B: 参数是字典 (标准结构) ===
        elif isinstance(raw_params, dict):
            resolved = raw_params.copy()
            
            # 1. 传统的显式替换逻辑 ($key)
            for k, v in resolved.items():
                if isinstance(v, str) and v.startswith("$"):
                    key_ref = v[1:]
                    if key_ref in self.context:
                        logger.info(f"Injecting dependency '{k}' <- context['{key_ref}']")
                        resolved[k] = self.context[key_ref]
            
            # 2. 隐式上下文注入
            # 即使参数是字典，我们也把"上一步结果"整理好放入一个保留字段
            # 这样 Agent 如果需要参考上一步，可以直接读取 _full_context
            if prev_output:
                combined_prompt = self._build_comprehensive_prompt(
                    prev_output=prev_output,
                    description=task.description,
                    current_instruction=str(raw_params)
                )
                resolved["_full_context"] = combined_prompt
                
                # 如果字典里没有任何显式依赖引用，且这是个 Agent 任务，
                # 有时我们希望把 input 字段自动填充为综合文本
                if "input" not in resolved and "query" not in resolved:
                     resolved["input"] = combined_prompt

            return resolved
            
        # === 情况 C: 无参数 ===
        else:
            if prev_output:
                combined_prompt = self._build_comprehensive_prompt(
                    prev_output=prev_output,
                    description=task.description,
                    current_instruction="Analyze the context provided."
                )
                return {"input": combined_prompt}
            return {}

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
        logger.info(f"Workflow {self.request_msg.parent_task_id} Completed.")
        
        # 构造最终结果
        final_result = TaskGroupResult(
            source=self.myAddress,
            destination=self.request_msg.original_sender or self.request_msg.source,
            group_id=self.request_msg.parent_task_id,
            results=self.step_results, # 返回所有步骤的详细结果
            failures={}
        )
        
        target = self.request_msg.original_sender or self.request_msg.source
        self.send(target, final_result)
        self.send(self.myAddress, ActorExitRequest())

    def _fail_workflow(self, error_msg: str) -> None:
        """失败"""
        logger.error(f"Workflow Terminated: {error_msg}")
        
        fail_result = TaskGroupResult(
            source=self.myAddress,
            destination=self.request_msg.original_sender or self.request_msg.source,
            group_id=self.request_msg.parent_task_id,
            results=self.step_results, # 返回已经成功的部分
            failures={"error": error_msg, "failed_step_index": self.current_step_index + 1}
        )
        
        target = self.request_msg.original_sender or self.request_msg.source
        self.send(target, fail_result)
        self.send(self.myAddress, ActorExitRequest())