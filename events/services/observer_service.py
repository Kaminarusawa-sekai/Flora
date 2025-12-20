import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set

from sqlalchemy.ext.asyncio import AsyncSession

# 导入本地模块
from ..common.event_instance import EventInstance
from ..common.enums import EventInstanceStatus
from ..common.events import (
    TaskStatusEvent,
    TaskStartedEvent,
    TaskCompletedEvent,
    TaskFailedEvent,
    TraceCancelledEvent,
    LoopRoundStartedEvent
)

# 导入外部依赖
from ..external.events.base import EventPublisher
from ..external.cache.base import CacheClient  # 需要 Cache 来读取大字段
from ..external.db.session import dialect
from ..external.db.impl import create_event_instance_repo


class ObserverService:
    def __init__(
        self,
        event_publisher: EventPublisher,
        cache: Optional[CacheClient] = None,  # 新增：用于读取 payload
        webhook_registry: Optional[Any] = None
    ):
        self.event_publisher = event_publisher
        self.cache = cache
        self.webhook_registry = webhook_registry

    async def on_task_status_changed(self, task: EventInstance) -> None:
        """
        处理任务状态变更事件（通常由 Worker 调用）
        """
        # 1. 构造基础状态事件
        event = TaskStatusEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            status=task.status.value,
            output_ref=task.output_ref,
            error_msg=task.error_msg,
            timestamp=datetime.now(timezone.utc)
        )
        
        # 2. 发布通用状态变更事件
        await self.event_publisher.publish("task.status.changed", event.model_dump())
        
        # 3. 发布细分事件（用于不同类型的订阅者）
        if task.status == EventInstanceStatus.RUNNING:
            await self._publish_task_started(task)
        elif task.status == EventInstanceStatus.SUCCESS:
            await self._publish_task_completed(task)
        elif task.status == EventInstanceStatus.FAILED:
            await self._publish_task_failed(task)
        
        # 4. 触发 Webhook
        if self.webhook_registry:
            await self._send_webhook_if_configured(task.trace_id, event)

    async def _publish_task_started(self, task: EventInstance) -> None:
        event = TaskStartedEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            worker_id=task.job_id,
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher.publish("task.started", event.model_dump())

    async def _publish_task_completed(self, task: EventInstance) -> None:
        event = TaskCompletedEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            output_ref=task.output_ref or "",
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher.publish("task.completed", event.model_dump())

    async def _publish_task_failed(self, task: EventInstance) -> None:
        event = TaskFailedEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            error_msg=task.error_msg or "Unknown error",
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher.publish("task.failed", event.model_dump())

    async def on_trace_cancelled(self, trace_id: str, reason: Optional[str] = None) -> None:
        event = TraceCancelledEvent(
            trace_id=trace_id,
            reason=reason,
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher.publish("trace.cancelled", event.model_dump())

    async def on_loop_round_started(self, task: EventInstance) -> None:
        event = LoopRoundStartedEvent(
            task_id=task.id,
            trace_id=task.trace_id,
            round_index=task.round_index or 0,
            timestamp=datetime.now(timezone.utc)
        )
        await self.event_publisher.publish("loop.round_started", event.model_dump())

    async def _send_webhook_if_configured(self, trace_id: str, event: Any) -> None:
        if not self.webhook_registry:
            return
        try:
            hooks = await self.webhook_registry.get_hooks(trace_id)
            for hook in hooks:
                # 实际发送逻辑
                pass
        except Exception:
            pass

    async def _send_webhook(self, url: str, event_data: Dict[str, Any]) -> None:
        """实际发送 Webhook 请求"""
        try:
            # 示例：实际场景应使用 aiohttp/httpx
            # async with httpx.AsyncClient() as client:
            #     await client.post(url, json=event_data)
            print(f"Sending webhook to {url}")
        except Exception as e:
            print(f"Webhook delivery failed: {e}")

    # ==========================================
    # 2. 对外查询服务 (Query API)
    # 针对 Lifecycle 和 Signal 进行了增强
    # ==========================================

    async def get_trace_summary(self, session: AsyncSession, trace_id: str) -> Dict[str, Any]:
        """
        获取 Trace 的聚合状态 (Dashboard 视图)
        增强：支持动态深度的统计
        """
        inst_repo = create_event_instance_repo(session, dialect)
        instances = await inst_repo.find_by_trace_id(trace_id)
        
        if not instances:
            return None

        # 基础统计
        summary = {
            "trace_id": trace_id,
            "total_tasks": len(instances),
            "status_counts": {},
            "max_depth": 0,
            "is_cancelled": False,
            "start_time": None,
            "end_time": None
        }

        # 遍历计算
        timestamps = []
        for inst in instances:
            # 统计状态
            s = inst.status.value
            summary["status_counts"][s] = summary["status_counts"].get(s, 0) + 1
            
            # 统计深度 (适配 expand_topology)
            if inst.depth > summary["max_depth"]:
                summary["max_depth"] = inst.depth
            
            # 检测是否被标记取消 (适配 SignalService)
            if hasattr(inst, 'control_signal') and inst.control_signal == "CANCEL":
                summary["is_cancelled"] = True

            # 计算时间跨度
            if inst.created_at:
                timestamps.append(inst.created_at)
            if inst.updated_at:
                timestamps.append(inst.updated_at)

        if timestamps:
            summary["start_time"] = min(timestamps)
            summary["end_time"] = max(timestamps) if summary["status_counts"].get("RUNNING", 0) == 0 else None

        return summary

    async def get_trace_graph(self, session: AsyncSession, trace_id: str) -> Dict[str, Any]:
        """
        【新功能】获取 Trace 的 DAG 结构树
        供前端绘制拓扑图使用，适配 LifecycleService 的动态裂变
        """
        inst_repo = create_event_instance_repo(session, dialect)
        instances = await inst_repo.find_by_trace_id(trace_id)
        
        # 1. 转换为字典映射
        node_map = {inst.id: inst for inst in instances}
        
        # 2. 构建树形结构 / 边列表
        nodes = []
        edges = []
        
        for inst in instances:
            # 节点信息 (精简版)
            nodes.append({
                "id": inst.id,
                "label": inst.name or inst.def_id,
                "status": inst.status.value,
                "depth": inst.depth,
                "type": inst.actor_type,
                # 如果被取消，前端可以显示特殊样式
                "signal": inst.control_signal if hasattr(inst, 'control_signal') else None
            })
            
            # 边信息 (通过 parent_id 构建)
            if inst.parent_id and inst.parent_id in node_map:
                edges.append({
                    "source": inst.parent_id,
                    "target": inst.id
                })
        
        return {
            "trace_id": trace_id,
            "nodes": nodes,
            "edges": edges
        }

    async def get_task_detail(
        self,
        session: AsyncSession,
        task_id: str,
        fetch_payload: bool = False
    ) -> Dict[str, Any]:
        """
        获取单个任务详情
        增强：支持从 input_ref / output_ref 还原真实大字段数据
        """
        inst_repo = create_event_instance_repo(session, dialect)
        task = await inst_repo.get(task_id)
        
        if not task:
            return None
            
        # 转换为字典
        # 假设 EventInstance 有 to_dict 方法，或者手动构建
        result = {
            "id": task.id,
            "trace_id": task.trace_id,
            "def_id": task.def_id,
            "name": task.name,
            "actor_type": task.actor_type,
            "status": task.status.value,
            "input_ref": task.input_ref,
            "output_ref": task.output_ref,
            "error_msg": task.error_msg,
            "depth": task.depth,
            "layer": task.layer,
            "parent_id": task.parent_id,
            "job_id": task.job_id,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "control_signal": task.control_signal if hasattr(task, 'control_signal') else None
        }
        
        # 如果需要，且存在 cache client，尝试还原大字段
        if fetch_payload and self.cache:
            if task.input_ref and task.input_ref.startswith("payload-"):
                # 模拟从 LifecycleService._save_payload 保存的地方读取
                # 实际 key 可能是 task.input_ref
                payload_data = await self.cache.get(task.input_ref)
                if payload_data:
                    result["input_params_full"] = payload_data
        
        return result

    # 保留原有方法以兼容旧代码
    async def get_task_instance(
        self,
        session: AsyncSession,
        task_id: str
    ) -> Optional[EventInstance]:
        """获取单个任务实例详情（兼容旧接口）"""
        inst_repo = create_event_instance_repo(session, dialect)
        return await inst_repo.get(task_id)

    async def get_trace_instances(
        self,
        session: AsyncSession,
        trace_id: str
    ) -> List[EventInstance]:
        """获取整个 Trace 的所有任务节点（兼容旧接口）"""
        inst_repo = create_event_instance_repo(session, dialect)
        return await inst_repo.find_by_trace_id(trace_id)

    async def get_ready_tasks(self, session: AsyncSession) -> List[EventInstance]:
        """
        获取当前准备就绪（PENDING 且无未完成依赖）的任务
        供调度器 (Scheduler/Dispatcher) 使用
        """
        inst_repo = create_event_instance_repo(session, dialect)
        return await inst_repo.find_ready_tasks()

    async def get_trace_status_summary(self, session: AsyncSession, trace_id: str) -> Dict[str, Any]:
        """
        获取 Trace 的状态摘要（兼容旧接口）
        """
        summary = await self.get_trace_summary(session, trace_id)
        if not summary:
            return None
        
        # 转换为旧格式
        status_counts = summary.get("status_counts", {})
        return {
            "trace_id": trace_id,
            "total": summary.get("total_tasks", 0),
            "pending": status_counts.get("PENDING", 0),
            "running": status_counts.get("RUNNING", 0),
            "success": status_counts.get("SUCCESS", 0),
            "failed": status_counts.get("FAILED", 0),
            "cancelled": status_counts.get("CANCELLED", 0),
            "skipped": status_counts.get("SKIPPED", 0),
            "depth": summary.get("max_depth", 0),
            "layers": 0,  # 旧字段，已废弃
            "is_complete": any(status_counts.values()) and all(
                status not in ["PENDING", "RUNNING"] 
                for status, count in status_counts.items() if count > 0
            )
        }
