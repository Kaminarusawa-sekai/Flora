
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from ..common.event_instance import EventInstance
from ..common.enums import EventInstanceStatus

from ..external.cache.base import CacheClient
from ..external.db.session import dialect
from ..external.db.impl import create_event_definition_repo, create_event_instance_repo
from ..external.events.bus import EventBus

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

    async def start_trace(
        self,
        session: AsyncSession,
        root_def_id: str,
        input_params: dict,
        trace_id: str,

    ) -> str:
        """
        启动链路，创建根节点并触发执行
        """
        # 1. 校验定义是否存在
        def_repo = create_event_definition_repo(session, dialect)
        definition = await def_repo.get(root_def_id)
        if not definition:
             raise ValueError(f"Definition {root_def_id} not found")

        # 2. 创建根节点
        root_id = str(uuid.uuid4())
        root = EventInstance(
            id=root_id,
            trace_id=trace_id,
            parent_id=None,
            job_id=f"job-{trace_id[:8]}",
            def_id=root_def_id,
            node_path="/",  # 根路径
            depth=0,
            actor_type=definition.actor_type,
            role=definition.role,
            status=EventInstanceStatus.RUNNING, # 根节点直接开始
            input_params={**definition.default_params, **input_params},
            input_ref=await self._save_payload(input_params), # 抽离大字段存储
            created_at=datetime.now(timezone.utc)
        )
        
        inst_repo = create_event_instance_repo(session, dialect)
        await inst_repo.create(root)
        
        # 【使用抽象】发送 TRACE_CREATED 事件
        # 告诉外界：有一个新链路开始了，根节点是 root_id
        await self.event_bus.publish(
            topic=self.topic_name,
            event_type="TRACE_CREATED",
            key=trace_id,
            payload={
                "root_instance_id": root_id,
                "def_id": root_def_id
            }
        )

        return trace_id

    async def expand_topology(
        self,
        session: AsyncSession,
        parent_id: str,
        subtasks_meta: list[dict],
        trace_id: str = None
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

