import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Set

from sqlalchemy.ext.asyncio import AsyncSession

# 导入本地模块
from common.event_instance import EventInstance
from common.enums import EventInstanceStatus

# 导入外部依赖
from external.cache.base import CacheClient
from external.db.session import dialect
from external.db.impl import create_event_instance_repo
from external.events.bus import EventBus
# 导入WebSocket管理器
from .websocket_manager import ConnectionManager

logger = logging.getLogger(__name__)

class ObserverService:
    def __init__(
        self,
        event_bus: EventBus,
        connection_manager: ConnectionManager,
        cache: Optional[CacheClient] = None,
        webhook_registry: Optional[Any] = None
    ):
        self.event_bus = event_bus
        self.connection_manager = connection_manager
        self.cache = cache
        self.webhook_registry = webhook_registry
        self.topic_name = "job_event_stream"

    # ==========================================
    # 1. 核心：对外查询服务 (Query API)
    # ==========================================

    async def get_trace_graph(self, session: AsyncSession, trace_id: str) -> Dict[str, Any]:
        """
        【核心】获取 Trace 的 DAG 结构树 (供前端 ReactFlow/X6 渲染)
        
        关键逻辑：
        数据库中 parent_id 存储的是父节点的【内部 UUID】，
        但前端展示通常需要【业务 task_id】作为节点的 ID。
        这里需要做一次映射。
        """
        inst_repo = create_event_instance_repo(session, dialect)
        instances = await inst_repo.find_by_trace_id(trace_id)
        
        if not instances:
            return {"trace_id": trace_id, "nodes": [], "edges": []}

        # 1. 建立 内部UUID -> 外部TaskID 的映射表
        uuid_to_task_id = {inst.id: inst.task_id for inst in instances} # 假设 inst.id 是PK
        
        nodes = []
        edges = []
        
        for inst in instances:
            # --- 节点信息 ---
            node_data = {
                "id": inst.task_id,      # 前端通过 task_id 索引
                "type": "customNode",    # 前端组件类型
                
                "label": inst.name or inst.task_id,
                "status": inst.status.value,
                "actor_type": inst.actor_type,
                "worker_id": inst.worker_id,
                "depth": inst.depth,
                # 将控制信号透传给前端，前端可显示"暂停"图标
                "signal": inst.control_signal if hasattr(inst, 'control_signal') else None,
                "created_at": inst.created_at.isoformat() if inst.created_at else None
                
            }
            nodes.append(node_data)
            
            # --- 边信息 (构建树状关系) ---
            if inst.parent_id:
                # 只有当父节点也在本次查询结果中时，才画边
                if inst.parent_id in uuid_to_task_id.values():
                    # parent_task_id = uuid_to_task_id[inst.parent_id]
                    parent_task_id = inst.parent_id
                    edges.append({
                        "id": f"e-{parent_task_id}-{inst.task_id}",
                        "source": parent_task_id,  # 必须是 task_id
                        "target": inst.task_id,    # 必须是 task_id
                        "animated": inst.status == EventInstanceStatus.RUNNING
                    })
        
        return {
            "trace_id": trace_id,
            "nodes": nodes,
            "edges": edges
        }

    async def get_trace_summary(self, session: AsyncSession, trace_id: str) -> Dict[str, Any]:
        """
        获取 Trace 的仪表盘统计数据
        """
        inst_repo = create_event_instance_repo(session, dialect)
        instances = await inst_repo.find_by_trace_id(trace_id)
        
        if not instances:
            return None

        # 初始化统计容器
        summary = {
            "trace_id": trace_id,
            "total_tasks": len(instances),
            "status_distribution": {
                "PENDING": 0, "RUNNING": 0, "SUCCESS": 0, "FAILED": 0, "CANCELLED": 0
            },
            "topology": {
                "max_depth": 0,
                "width_at_depth": {}
            },
            "control_state": "NORMAL", # NORMAL, PAUSED, CANCELLED
            "duration": 0
        }

        timestamps = []
        
        for inst in instances:
            # 1. 状态计数
            s = inst.status.value
            if s in summary["status_distribution"]:
                summary["status_distribution"][s] += 1
            
            # 2. 拓扑统计
            summary["topology"]["max_depth"] = max(summary["topology"]["max_depth"], inst.depth)
            
            # 3. 检查控制信号 (只要有一个节点被取消，往往意味着子树被取消)
            # 这里取根节点或当前节点的信号作为 trace 信号的参考
            if inst.depth == 0 and hasattr(inst, 'control_signal') and inst.control_signal:
                summary["control_state"] = inst.control_signal

            # 4. 时间范围
            if inst.created_at: timestamps.append(inst.created_at)
            if hasattr(inst, 'finished_at') and inst.finished_at: 
                timestamps.append(inst.finished_at)

        # 计算耗时
        if timestamps:
            start_t = min(timestamps)
            end_t = max(timestamps)
            # 只有当所有任务都不处于 RUNNING 时，end_t 才有最终意义，否则就是 "至今"
            if summary["status_distribution"]["RUNNING"] > 0:
                end_t = datetime.now(timezone.utc)
            
            summary["start_time"] = start_t
            summary["duration_seconds"] = (end_t - start_t).total_seconds()

        return summary

    async def get_trace_detail(self, session: AsyncSession, trace_id: str) -> List[Dict[str, Any]]:
        """
        获取 Trace 详情列表 (表格视图)
        """
        inst_repo = create_event_instance_repo(session, dialect)
        tasks = await inst_repo.find_by_trace_id(trace_id)
        
        # 预先构建 ID 映射，为了在列表中显示 Parent Name
        uuid_map = {t.id: t for t in tasks}

        results = []
        for task in tasks:
            parent = uuid_map.get(task.parent_id)
            
            item = {
                "task_id": task.task_id,
                "name": task.name,
                "status": task.status.value,
                "worker_id": task.worker_id,
                "depth": task.depth,
                "parent_task_id": parent.task_id if parent else None,
                "created_at": task.created_at,
                "finished_at": getattr(task, 'finished_at', None),
                "error_msg": task.error_detail.get("msg") if hasattr(task, 'error_detail') and task.error_detail else None,
                # 透传 payload_snapshot 的一部分用于预览
                "input_preview": str(task.input_params)[:100] if hasattr(task, 'input_params') and task.input_params else None
            }
            results.append(item)
            
        return results

    async def find_traces_by_user_id(
        self,
        session: AsyncSession,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        根据user_id查询所有trace_id及其状态，支持时间范围过滤
        
        Args:
            user_id: 用户ID
            start_time: 开始时间，可选
            end_time: 结束时间，可选
            limit: 每页数量，默认100
            offset: 偏移量，默认0
            
        Returns:
            List[Dict[str, Any]]: trace列表，包含trace_id、创建时间和最新状态
        """
        inst_repo = create_event_instance_repo(session, dialect)
        return await inst_repo.find_traces_by_user_id(user_id, start_time, end_time, limit, offset)
    
    # ==========================================
    # 2. 核心：WebSocket 消息泵 (Event Pump)
    # ==========================================

    async def start_listening(self) -> None:
        """
        监听 Redis/EventBus，转换格式，并推送到 WebSocket。
        这是 ObserverService 真正的核心，连接了 LifecycleService(写) 和 Frontend(读)。
        """
        logger.info(f"ObserverService started listening on topic: {self.topic_name}")
        
        # 订阅 LifecycleService 发出的事件
        async for message in self.event_bus.subscribe(self.topic_name):
            try:
                event_type = message.get("event_type")
                trace_id = message.get("key") # key 通常是 trace_id
                payload = message.get("payload", {})

                if not trace_id:
                    continue

                socket_msg = None

                # -----------------------------------------------
                # 场景 A: 拓扑结构变化 (图谱要重画/增加节点)
                # -----------------------------------------------
                if event_type == "TRACE_CREATED":
                    socket_msg = {
                        "event": "trace_created",
                        "data": {
                            "trace_id": trace_id,
                            "root_task_id": payload.get("root_instance_id") # 注意字段匹配
                        }
                    }

                elif event_type == "TOPOLOGY_EXPANDED":
                    # LifecycleService 发出的是 parent_id 和 new_instance_ids
                    # 前端需要知道在哪儿加了谁
                    socket_msg = {
                        "event": "graph_updated",
                        "data": {
                            "parent_task_id": payload.get("parent_id"), # 确保是 task_id
                            "new_children_ids": payload.get("new_instance_ids"),
                            "count": payload.get("count")
                        }
                    }

                # -----------------------------------------------
                # 场景 B: 节点状态流转 (节点变色)
                # -----------------------------------------------
                elif event_type in ["TASK_STARTED", "TASK_RUNNING"]:
                    socket_msg = {
                        "event": "node_updated",
                        "data": {
                            "node_id": payload.get("task_id"),
                            "status": "RUNNING",
                            "worker_id": payload.get("worker_id"),
                            "progress": payload.get("progress", 0)
                        }
                    }

                elif event_type == "TASK_COMPLETED":
                    socket_msg = {
                        "event": "node_updated",
                        "data": {
                            "node_id": payload.get("task_id"),
                            "status": "SUCCESS",
                            "progress": 100,
                            # 可选：携带少量结果摘要
                            "output_summary": str(payload.get("data", ""))[:50]
                        }
                    }

                elif event_type == "TASK_FAILED":
                    socket_msg = {
                        "event": "node_updated",
                        "data": {
                            "node_id": payload.get("task_id"),
                            "status": "FAILED",
                            "error": payload.get("error_msg")
                        }
                    }

                # -----------------------------------------------
                # 场景 C: 实时心跳 (UI 动效)
                # -----------------------------------------------
                elif event_type == "AGENT_HEARTBEAT":
                    # Payload: { "agent_id": "...", "task_info": { "task_id": "...", "step": 1 } }
                    task_info = payload.get("task_info") or {}
                    if task_info:
                        socket_msg = {
                            "event": "agent_activity",
                            "data": {
                                "agent_id": payload.get("agent_id"),
                                "node_id": task_info.get("task_id"),
                                "step": task_info.get("step")
                            }
                        }

                # -----------------------------------------------
                # 执行推送
                # -----------------------------------------------
                if socket_msg:
                    # 推送给正在查看该 Trace 的所有前端客户端
                    await self.connection_manager.broadcast_to_trace(trace_id, socket_msg)
                    
                    # (可选) 如果配置了 Webhook，这里也可以异步触发
                    if self.webhook_registry:
                        asyncio.create_task(self._trigger_webhook(trace_id, socket_msg))

            except Exception as e:
                logger.error(f"Error processing event in Observer: {e}", exc_info=True)
                continue

    async def _trigger_webhook(self, trace_id: str, payload: dict):
        """WebHook 触发逻辑 (Placeholder)"""
        pass
