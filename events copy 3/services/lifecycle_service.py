import uuid
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from ..common.task_instance import TaskInstance
from ..common.enums import TaskInstanceStatus
from ..external.messaging.base import MessageBroker
from ..external.cache.base import CacheClient
from ..external.db.session import dialect
from ..external.db.impl import create_task_definition_repo, create_task_instance_repo


class LifecycleService:
    def __init__(
        self,
        broker: MessageBroker,
        cache: Optional[CacheClient] = None
    ):
        self.broker = broker
        self.cache = cache

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
        input_params: dict
    ) -> str:
        """
        启动链路，创建根节点并触发执行
        """
        # 1. 校验定义是否存在
        def_repo = create_task_definition_repo(session, dialect)
        definition = await def_repo.get(root_def_id)
        if not definition:
             raise ValueError(f"Definition {root_def_id} not found")

        # 2. 创建根节点
        trace_id = str(uuid.uuid4())
        root_id = str(uuid.uuid4())
        
        root = TaskInstance(
            id=root_id,
            trace_id=trace_id,
            parent_id=None,
            job_id=f"job-{trace_id[:8]}",
            def_id=root_def_id,
            node_path="/",  # 根路径
            depth=0,
            actor_type=definition.actor_type,
            role=definition.role,
            status=TaskInstanceStatus.RUNNING, # 根节点直接开始
            input_params={**definition.default_params, **input_params},
            input_ref=await self._save_payload(input_params), # 抽离大字段存储
            created_at=datetime.now(timezone.utc)
        )
        
        inst_repo = create_task_instance_repo(session, dialect)
        await inst_repo.create(root)
        
        # 3. 触发执行 (发送给 Agent Actor)
        await self.broker.publish("agent.run", {
            "trace_id": trace_id,
            "instance_id": root_id
        })
        return trace_id

    async def expand_topology(
        self,
        session: AsyncSession,
        parent_id: str,
        subtasks_meta: list[dict]
    ) -> List[str]:
        """
        动态拓扑扩展
        Agent 调用此方法：我在 parent_id 下生成了 DAG。
        subtasks_meta 示例: [
           {"def_id": "AGG_GROUP", "name": "Group A", "params": {...}},
           {"def_id": "AGG_GROUP", "name": "Group B", "params": {...}}
        ]
        """
        inst_repo = create_task_instance_repo(session, dialect)
        parent = await inst_repo.get(parent_id)
        
        # 1. 检查父节点状态：如果父节点已经被取消，禁止裂变！
        if parent.control_signal == "CANCEL":
            raise ValueError("Parent task is cancelled")

        new_instances = []
        new_ids = []
        
        for meta in subtasks_meta:
            child_id = str(uuid.uuid4())
            new_ids.append(child_id)
            
            # 获取子任务定义
            def_repo = create_task_definition_repo(session, dialect)
            child_def = await def_repo.get(meta["def_id"])
            if not child_def:
                raise ValueError(f"Definition {meta['def_id']} not found")
            
            child = TaskInstance(
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
                status=TaskInstanceStatus.PENDING, # 初始为 PENDING，等待调度
                input_params={**child_def.default_params, **meta.get("params", {})},
                input_ref=await self._save_payload(meta.get("params", {})),
                created_at=datetime.now(timezone.utc)
            )
            new_instances.append(child)
            
        await inst_repo.bulk_create(new_instances)
        
        return new_ids

    async def _schedule_task(self, task: TaskInstance):
        # 统一入口：所有任务派发走 broker.publish_delayed，支持延时和重试
        await self.broker.publish_delayed("task.execute", {"instance_id": task.id}, delay_sec=0)