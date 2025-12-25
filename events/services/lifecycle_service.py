
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from common.event_instance import EventInstance
from common.event_log import EventLog
from common.enums import EventInstanceStatus

from external.cache.base import CacheClient
from external.db.session import dialect
from external.db.impl import create_event_definition_repo, create_event_instance_repo, create_event_log_repo
from external.events.bus import EventBus

##TODO:这里有双写一致性问题，后期再解决
class LifecycleService:
    def __init__(
        self,
        event_bus: EventBus,
        cache: Optional[CacheClient] = None
    ):
        self.event_bus = event_bus
        self.cache = cache
        self.topic_name = "job_event_stream"

    async def _save_payload(self, payload: dict) -> str:
        """
        保存大字段到外部存储（如 OSS/S3 或 Redis）
        目前简化实现，直接返回一个模拟的 key
        """
        # 实际实现中，这里应该将 payload 保存到外部存储
        # 并返回对应的引用 key
        return f"payload-{str(uuid.uuid4())[:8]}"

    async def _record_event_log(self, session: AsyncSession, instance: EventInstance, event_type: str, payload: dict, error: str = None):
        """
        【新增辅助方法】通用流水账记录
        对应执行系统的每一次“上报”
        """
        log_repo = create_event_log_repo(session, dialect)
        log_entry = EventLog(
            id=str(uuid.uuid4()),
            instance_id=instance.id,
            trace_id=instance.trace_id,
            event_type=event_type,
            level="ERROR" if error else "INFO",
            content=f"State changed to {event_type}",
            payload_snapshot=payload.get("enriched_context_snapshot"), # 记录当时的快照
            error_detail={"msg": error} if error else None,
            execution_node=payload.get("execution_node"),
            agent_id=payload.get("agent_id"),
            created_at=datetime.now(timezone.utc)
        )
        await log_repo.create(log_entry)

    async def start_trace(
        self,
        session: AsyncSession,
        root_def_id: str,
        input_params: dict,
        request_id: str,                # 【新增】必须传入 request_id 用于关联
        trace_id: Optional[str] = None, # 【修改】变为可选，如果不传则内部生成
        user_id: Optional[str] = None   # 记录是谁触发的

    ) -> str:
        """
        启动链路
        维护 request_id (1) -> trace_id (N) 的关系
        """
        # 1. 校验定义是否存在
        def_repo = create_event_definition_repo(session, dialect)
        definition = await def_repo.get(root_def_id)
        if not definition:
             raise ValueError(f"Definition {root_def_id} not found")

        # 2. 【修改】生成 trace_id (如果外部没传)
        if not trace_id:
            trace_id = str(uuid.uuid4())

        # 3. 创建根节点
        root_id = str(uuid.uuid4())
        root = EventInstance(
            id=root_id,
            trace_id=trace_id,
            request_id=request_id,   # 【新增】关键：将 request_id 写入根节点
            parent_id=None,
            job_id=f"job-{trace_id[:8]}",
            def_id=root_def_id,
            node_path="/",  # 根路径
            depth=0,
            actor_type=definition.actor_type,
            role=definition.role,
            status=EventInstanceStatus.PENDING, # 根节点直接开始
            input_params={**definition.default_params, **input_params},
            input_ref=await self._save_payload(input_params), # 抽离大字段存储
            # 【新增】初始快照
            runtime_state_snapshot={"lifecycle": "created"},
            created_at=datetime.now(timezone.utc)
        )
        
        inst_repo = create_event_instance_repo(session, dialect)
        await inst_repo.create(root)
        
        # 【新增】记录 EventLog (历史轨迹)
        # 即使是创建，也应该是一条 Log，方便回溯 "什么时候开始的"
        await self._record_event_log(
            session,
            root,
            event_type="STARTED",
            payload={
                "user_id": user_id, 
                "request_id": request_id, # Log 里也记一下
                "params_preview": str(input_params)[:100]
            }
        )
        
        # 【使用抽象】发送 TRACE_CREATED 事件
        # 告诉外界：有一个新链路开始了，根节点是 root_id
        await self.event_bus.publish(
            topic=self.topic_name,
            event_type="TRACE_CREATED",
            key=trace_id,
            payload={
                "root_instance_id": root_id,
                "def_id": root_def_id,
                "request_id": request_id, # 通知下游，这个 trace 属于哪个 request
                "trace_id": trace_id      # 返回生成的 trace_id
            }
        )

        return trace_id

    async def get_latest_trace_by_request(self, session: AsyncSession, request_id: str) -> Optional[str]:
        """
        根据 request_id 获取最新的 trace_id
        """
        from sqlalchemy import select, desc
        from ..external.db.models import EventInstanceDB
        
        # 只需要查根节点 (parent_id 为空)
        stmt = (
            select(EventInstanceDB.trace_id)
            .where(
                EventInstanceDB.request_id == request_id,
                EventInstanceDB.parent_id == None  # 根节点
            )
            .order_by(desc(EventInstanceDB.created_at)) # 最新的在前
            .limit(1)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def expand_topology(
        self,
        session: AsyncSession,
        parent_id: str,
        subtasks_meta: list[dict],
        trace_id: str = None,
        context_snapshot: Dict = None  # 新增：接收上下文快照
    ) -> List[str]:
        """
        动态拓扑扩展
        Agent 调用此方法：我在 parent_id 下生成了 DAG。
        subtasks_meta 示例: [
           {"id": "external-id-1", "def_id": "AGG_GROUP", "name": "Group A", "params": {...}},
           {"id": "external-id-2", "def_id": "AGG_GROUP", "name": "Group B", "params": {...}}
        ]
        """
        # 【修改点 1】: 快速失败 (Fast Fail)
        # 在查数据库之前，先查缓存。如果整个 Trace 已经被杀掉，直接抛异常，省一次 DB 查询。
        if trace_id and self.cache:
            # 这里的 key 必须和 SignalService 里的 key 保持绝对一致
            cached_signal = await self.cache.get(f"trace_signal:{trace_id}")
            if cached_signal == "CANCEL":
                raise ValueError(f"Trace {trace_id} has been cancelled (Cache Hit)")

        inst_repo = create_event_instance_repo(session, dialect)
        parent = await inst_repo.get(parent_id)
        
        if not parent:
            raise ValueError(f"Parent {parent_id} not found")
        
        # 【新增校验】确保父节点属于当前 URL 指定的 trace
        if trace_id and parent.trace_id != trace_id:
            raise ValueError(f"Parent node {parent_id} does not belong to trace {trace_id}")
        
        # 【修改点 2】: 数据库层面的二次确认 (Double Check)
        # 防止缓存过期或未命中的情况
        if parent.control_signal == "CANCEL":
            raise ValueError("Parent event is cancelled")

        new_instances = []
        new_ids = []
        
        for meta in subtasks_meta:
            # 从外部输入获取id
            if "id" not in meta:
                raise ValueError(f"Missing required 'id' field in subtask meta: {meta}")
            child_id = meta["id"]
            new_ids.append(child_id)
            
            # 获取子任务定义
            def_repo = create_event_definition_repo(session, dialect)
            child_def = await def_repo.get(meta["def_id"])
            if not child_def:
                raise ValueError(f"Definition {meta['def_id']} not found")
            
            child = EventInstance(
                id=child_id,
                trace_id=parent.trace_id,
                parent_id=parent.id,
                job_id=parent.job_id,
                def_id=meta["def_id"], # 必须关联到具体的 Definition
                
                # 【关键】构建物化路径
                node_path=f"{parent.node_path}{parent.id}/",
                depth=parent.depth + 1,
                
                actor_type=child_def.actor_type,
                role=child_def.role,
                name=meta.get("name"),
                status=EventInstanceStatus.PENDING, # 初始为 PENDING，等待调度
                input_params={**child_def.default_params, **meta.get("params", {})},
                input_ref=await self._save_payload(meta.get("params", {})),
                created_at=datetime.now(timezone.utc),
                # 【修改点 3】: 状态继承 (Inheritance)
                # 关键！如果父节点有信号（比如 PAUSE），子节点必须继承。
                control_signal=parent.control_signal
            )
            new_instances.append(child)
            
        await inst_repo.bulk_create(new_instances)
        
        # 【新增】记录 Parent 的 EventLog
        # 记录 "我生了孩子" 这一事件
        await self._record_event_log(
            session,
            parent,
            event_type="TOPOLOGY_EXPANDED",
            payload={
                "new_children_count": len(new_ids),
                "children_ids": new_ids,
                # 优先使用传入的 snapshot，如果没有则使用默认
                "enriched_context_snapshot": context_snapshot or {"action": "spawn_subtasks"}
            }
        )
        
        # 【使用抽象】发送 TOPOLOGY_EXPANDED 事件
        # 告诉外界：parent_id 下面裂变出了 new_ids 这些新任务
        if new_ids:
            await self.event_bus.publish(
                topic=self.topic_name,
                event_type="TOPOLOGY_EXPANDED",
                key=parent.trace_id,
                payload={
                    "parent_id": parent_id,
                    "new_instance_ids": new_ids,
                    "count": len(new_ids)
                }
            )
        
        return new_ids

    # ------------------------------------------------------
    # 场景3：【核心新增】同步执行状态 (对接执行系统的 Args)
    # ------------------------------------------------------
    async def sync_execution_state(
        self,
        session: AsyncSession,
        execution_args: dict
    ):
        """
        接收执行系统的 Args 对象，更新 Instance 状态并记录 Log
        execution_args: 即你提供的 Args 数据结构
        """
        task_id = execution_args.get("task_id")
        event_type = execution_args.get("event_type") # STARTED, RUNNING, COMPLETED, FAILED
        snapshot = execution_args.get("enriched_context_snapshot")
        data = execution_args.get("data")
        error_msg = execution_args.get("error")

        inst_repo = create_event_instance_repo(session, dialect)
        instance = await inst_repo.get(task_id)
        
        if not instance:
            # 极端情况：收到事件但找不到任务（可能是创建消息延迟了）
            # 可以选择抛错或者创建一个“孤儿任务”记录
            print(f"Warning: Received event {event_type} for unknown task {task_id}")
            return

        # 1. 更新 EventInstance (最新态)
        # 根据 event_type 映射状态
        update_fields = {"updated_at": datetime.now(timezone.utc)}
        
        if event_type == "STARTED":
            update_fields["status"] = EventInstanceStatus.RUNNING
            update_fields["started_at"] = datetime.now(timezone.utc)
        
        elif event_type == "COMPLETED":
            update_fields["status"] = EventInstanceStatus.SUCCESS
            update_fields["finished_at"] = datetime.now(timezone.utc)
            update_fields["progress"] = 100
            # 处理输出数据
            if data:
                # 假设执行系统已经处理好大字段，这里 data 可能是引用或小字段
                update_fields["output_ref"] = str(data)
        
        elif event_type == "FAILED":
            update_fields["status"] = EventInstanceStatus.FAILED
            update_fields["finished_at"] = datetime.now(timezone.utc)
            update_fields["error_detail"] = {"msg": error_msg} # 更新 Instance 上的错误摘要
            
        elif event_type == "PROGRESS":
            # 假设 data 里有 percent
            if isinstance(data, dict) and "percent" in data:
                update_fields["progress"] = data["percent"]

        # 更新快照 (始终保持最新)
        if snapshot:
            update_fields["runtime_state_snapshot"] = snapshot

        # 执行更新
        for k, v in update_fields.items():
            setattr(instance, k, v)
        await inst_repo.update_fields(task_id, **update_fields) # 保存更新

        # 2. 插入 EventLog (流水态)
        # 无论 update_fields 变没变，Log 都要记，因为这是“发生了一件事”
        await self._record_event_log(
            session,
            instance,
            event_type=event_type,
            payload=execution_args, # 把整个 Args 存下来或者存关键部分
            error=error_msg
        )

        # 3. 如果需要，转发给前端或其他系统
        await self.event_bus.publish(
            topic=self.topic_name,
            event_type=f"TASK_{event_type}", # 比如 TASK_COMPLETED
            key=instance.trace_id,
            payload={
                "task_id": task_id,
                "status": update_fields.get("status"),
                "progress": update_fields.get("progress")
            }
        )

