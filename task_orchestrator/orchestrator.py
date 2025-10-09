# app/orchestrator.py
import asyncio
import time
import uuid
from typing import Dict, Any, Optional
from task_orchestrator.context import current_task_id, current_frame_id
from task_orchestrator.task_frame import TaskFrame
from task_orchestrator.task_execution_graph import TaskExecutionGraph
from agent.agent_registry import AgentRegistry
from actor_manager.actor_manager import ActorManager

TaskStatus = {
    "PENDING": "pending",
    "RUNNING": "running",
    "COMPLETED": "completed",
    "FAILED": "failed"
}

class TaskOrchestrator:

    _instance = None
    _lock = asyncio.Lock()  # 用于异步环境下的线程安全（协程安全）

    def __new__(cls, agent_registry: AgentRegistry = None):
        if cls._instance is None:
            # 注意：__new__ 是类方法，不能直接 await，但我们可以在首次创建时要求传入 agent_registry
            if agent_registry is None:
                raise ValueError("TaskOrchestrator singleton requires an AgentRegistry on first instantiation.")
            cls._instance = super(TaskOrchestrator, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, agent_registry: AgentRegistry):
         # 防止多次初始化
        if self._initialized:
            return
        self.agent_registry = agent_registry
        self.graphs: Dict[str, TaskExecutionGraph] = {}
        self._futures: Dict[str, asyncio.Future] = {}      # frame_id → future
        self._task_done_futures: Dict[str, asyncio.Future] = {}  # task_id → future
        self.max_task_duration = 300

    @classmethod
    async def get_instance(cls, agent_registry: AgentRegistry = None) -> "TaskOrchestrator":
        """
        异步安全地获取单例实例。
        首次调用必须传入 agent_registry。
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    if agent_registry is None:
                        raise ValueError("AgentRegistry is required to initialize TaskOrchestrator.")
                    cls._instance = cls(agent_registry)
        return cls._instance

    async def submit_task(
        self,
        entry_agent_id: str,
        initial_context: Dict[str, Any],
        tenant_id: str,
        capability: str=None,
    ) -> str:
        task_id = f"task_{uuid.uuid4().hex}"
        token = current_task_id.set(task_id)

        # 确保上下文包含必要字段（用于子帧继承）
        context = {
            "task_id": task_id,
            "tenant_id": tenant_id,
            **initial_context
        }


        try:
            frame_id = f"frame_{task_id}_root"
            root_frame = TaskFrame(
                frame_id=frame_id,
                task_id=task_id,
                caller_agent_id="system",
                target_agent_id=entry_agent_id,
                capability=capability,
                context=context,
                parent_frame_id=None,
                tenant_id=tenant_id,
                # status="pending"
            )

            orchestrator = await TaskOrchestrator.get_instance()
            graph = orchestrator.get_graph(task_id)
            graph.add_frame(root_frame)

            # 注册 future（可选）
            orchestrator.register_future_for_frame(frame_id)

            # 👇 关键：Orchestrator 主动向根 Agent 发送执行消息
            actor_manager = ActorManager.get_instance()
            root_actor = actor_manager.get_or_create_actor(tenant_id, entry_agent_id)
            root_actor.send_message({
                "type": "execute_frame",
                "frame_id": frame_id,
                "task_id": task_id,
                "tenant_id": tenant_id
            })

            return task_id
        finally:
            current_task_id.reset(token)

    def mark_frame_completed(self, frame_id: str, result: Any):
        graph = self._get_graph_by_frame(frame_id)
        frame = graph.get_frame(frame_id)
        frame.status = "completed"
        frame.result = result

        if frame_id in self._futures:
            self._futures[frame_id].set_result({"status": "ok", "result": result})

        self._check_and_mark_task_done(frame.task_id)
        self._try_aggregate_parent(frame)

    def mark_frame_failed(self, frame_id: str, error: str):
        graph = self._get_graph_by_frame(frame_id)
        frame = graph.get_frame(frame_id)
        frame.status = "failed"
        frame.error = error

        if frame_id in self._futures:
            self._futures[frame_id].set_result({"status": "error", "error": error})

        self._check_and_mark_task_done(frame.task_id)
        self._try_aggregate_parent(frame)

    def _check_and_mark_task_done(self, task_id: str):
        graph = self.graphs[task_id]
        if graph.is_all_roots_done():
            future = self._task_done_futures.get(task_id)
            if future and not future.done():
                # 收集所有根帧结果
                results = []
                for rid in graph.root_frame_ids:
                    rf = graph.get_frame(rid)
                    if rf.status == "completed":
                        results.append({"frame_id": rid, "result": rf.result})
                    else:
                        results.append({"frame_id": rid, "error": rf.error})
                future.set_result(results)

    def _get_graph_by_frame(self, frame_id: str) -> TaskExecutionGraph:
        for graph in self.graphs.values():
            if frame_id in graph.frames:
                return graph
        raise KeyError(f"Frame {frame_id} not found in any graph")

    # ===== 兼容接口 =====
    def get_task_done_future(self, task_id: str) -> asyncio.Future:
        return self._task_done_futures[task_id]

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        if task_id not in self.graphs:
            return None
        graph = self.graphs[task_id]
        if not graph.root_frame_ids:
            return {"status": "pending"}
        if graph.is_all_roots_done():
            # 检查是否有失败
            any_failed = any(
                graph.get_frame(rid).status == "failed"
                for rid in graph.root_frame_ids
            )
            status = "failed" if any_failed else "completed"
        else:
            status = "running"
        return {"status": status, "task_id": task_id}

    async def _run_frame_with_context(self, frame_id: str):
        """在 task 上下文中运行帧"""
        # 从 frame_id 反推 task_id（简化：假设格式为 frame_{task_id}_...）
        task_id = frame_id.split("_", 2)[1]
        token = current_task_id.set(task_id)
        try:
            await _run_frame(frame_id)  # 复用你已有的 _run_frame 逻辑
        finally:
            current_task_id.reset(token)

    def register_future_for_frame(self, frame_id: str) -> asyncio.Future:
        fut = asyncio.Future()
        self._futures[frame_id] = fut
        return fut

    def get_future(self, frame_id: str) -> asyncio.Future:
        return self._futures[frame_id]

    def get_graph(self, task_id: str) -> TaskExecutionGraph:
        return self.graphs[task_id]

    def get_graph_for_frame(self, frame_id: str) -> TaskExecutionGraph:
        for graph in self.graphs.values():
            if frame_id in graph.frames:
                return graph
        raise KeyError(f"Frame {frame_id} not found")

    # def mark_frame_completed(self, frame_id: str, result: Any):
    #     graph = self.get_graph_for_frame(frame_id)
    #     frame = graph.get_frame(frame_id)
    #     frame.status = "completed"
    #     frame.result = result

    #     if frame_id in self._futures:
    #         self._futures[frame_id].set_result({"status": "ok", "result": result})

    #     self._try_aggregate_parent(frame)

    # def mark_frame_failed(self, frame_id: str, error: str):
    #     graph = self.get_graph_for_frame(frame_id)
    #     frame = graph.get_frame(frame_id)
    #     frame.status = "failed"
    #     frame.error = error

    #     if frame_id in self._futures:
    #         self._futures[frame_id].set_result({"status": "error", "error": error})

    #     self._try_aggregate_parent(frame)

    def _try_aggregate_parent(self, child_frame: TaskFrame):
        if child_frame.parent_frame_id is None:
            return

        parent_id = child_frame.parent_frame_id
        graph = self.get_graph_for_frame(parent_id)
        parent = graph.get_frame(parent_id)

        if graph.are_all_children_done(parent_id) and parent.status == "pending":
            # 简化聚合：收集所有子结果
            child_results = []
            for cid in parent.sub_frames:
                cf = graph.get_frame(cid)
                if cf.status == "completed":
                    child_results.append(cf.result)
                else:
                    child_results.append({"error": cf.error})
            self.mark_frame_completed(parent_id, child_results)

    # ===== 兼容旧接口 =====
    # def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
    #     if task_id not in self.graphs:
    #         return None
    #     graph = self.graphs[task_id]
    #     # 任务状态 = 所有根帧是否完成
    #     if not graph.root_frame_ids:
    #         return {"status": "pending", "task_id": task_id}
    #     all_done = graph.is_all_roots_done()
    #     if not all_done:
    #         return {"status": "running", "task_id": task_id}
    #     # 检查是否有失败
    #     any_failed = any(
    #         graph.get_frame(rid).status == "failed"
    #         for rid in graph.root_frame_ids
    #     )
    #     status = "failed" if any_failed else "completed"
    #     return {"status": status, "task_id": task_id}

    def get_task_result(self, task_id: str) -> Optional[Any]:
        status_info = self.get_task_status(task_id)
        if not status_info or status_info["status"] != "completed":
            return None
        graph = self.graphs[task_id]
        # 返回所有根帧的结果（列表）
        return [
            graph.get_frame(rid).result
            for rid in graph.root_frame_ids
        ]

    def cleanup_expired_tasks(self):
        now = time.time()
        expired = []
        for task_id, graph in self.graphs.items():
            # 用第一个根帧的创建时间作为任务开始时间
            if not graph.root_frame_ids:
                continue
            start_time = graph.get_frame(graph.root_frame_ids[0]).created_at
            if now - start_time > self.max_task_duration:
                # 标记所有 pending 帧为超时
                for frame in graph.frames.values():
                    if frame.status == "pending":
                        self.mark_frame_failed(frame.frame_id, "Task timeout")
                expired.append(task_id)

        # 可选：清理 expired graphs（或保留用于审计）

    # In TaskOrchestrator
    async def on_frame_completed(self, frame_id: str):
        graph = self.get_graph_by_frame(frame_id)
        frame = graph.get_frame(frame_id)

        # 获取该 frame 的所有 direct children（在 execute_frame 中已注册）
        child_frames = graph.get_direct_children(frame_id)

        for child in child_frames:
            if child.status == "pending":
                # 发送执行消息
                actor_manager = ActorManager.get_instance()
                actor = actor_manager.get_or_create_actor(
                    tenant_id=child.tenant_id,
                    agent_id=child.target_agent_id
                )
                actor.send_message({
                    "type": "execute_frame",
                    "frame_id": child.frame_id,
                    "task_id": child.task_id,
                    "tenant_id": child.tenant_id
                })




async def execute_frame(
    *,
    target_agent_id: str,
    capability: str,
    context: Dict[str, Any],
    parent_frame_id: Optional[str] = None,
    caller_agent_id: str = "system"
) -> str:
    task_id = current_task_id.get()
    if task_id is None:
        raise RuntimeError("execute_frame() must be called inside a task context")

    # 从当前帧或任务上下文获取 tenant_id
    tenant_id = context.get("tenant_id")
    if not tenant_id:
        # 或从 parent_frame 推导
        if parent_frame_id:
            graph = (await TaskOrchestrator.get_instance()).get_graph(task_id)
            parent = graph.get_frame(parent_frame_id)
            tenant_id = parent.tenant_id
        else:
            raise ValueError("tenant_id required in root call")

    frame_id = f"frame_{task_id}_{uuid.uuid4().hex}"
    frame = TaskFrame(
        frame_id=frame_id,
        task_id=task_id,
        caller_agent_id=caller_agent_id,
        target_agent_id=target_agent_id,
        capability=capability,
        context=context,
        parent_frame_id=parent_frame_id,
        tenant_id=tenant_id,
        status="pending",
    )

    orchestrator = await TaskOrchestrator.get_instance()
    graph = orchestrator.get_graph(task_id)
    graph.add_frame(frame)

    orchestrator.register_future_for_frame(frame_id)

    # ❌ 不发消息！由 orchestrator 在父帧完成后统一触发
    return frame_id

async def _run_frame(frame_id: str):
    task_id = current_task_id.get()
    if task_id is None:
        raise RuntimeError("Frame executed outside task context")

    token = current_frame_id.set(frame_id)
    orchestrator = await TaskOrchestrator.get_instance()
    try:
        graph = orchestrator.get_graph(task_id)
        frame = graph.get_frame(frame_id)
        agent_registry = AgentRegistry.get_instance()
        agent = agent_registry.get_agent(frame.target_agent_id) ##TODO: error handling
        result = await agent.execute(frame.capability, frame.context)

        orchestrator.mark_frame_completed(frame_id, result)
    except Exception as e:
        orchestrator.mark_frame_failed(frame_id, str(e))
    finally:
        current_frame_id.reset(token)