
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

# 导入正确的模块
from common.event_instance import EventInstance
from common.event_log import EventLog
from common.enums import EventInstanceStatus
from external.cache.base import CacheClient
from external.db.session import dialect
from external.db.impl import create_event_definition_repo, create_event_instance_repo, create_event_log_repo
from external.events.bus import EventBus

##TODO:这里有双写一致性问题，后期再解决
##TODO：这里的定义可能不需要，后期考虑移除
class LifecycleService:
    def __init__(
        self,
        event_bus: EventBus,
        cache: CacheClient  # 此时 Cache 变得至关重要，不再是 Optional，或者内部要做兜底
    ):
        self.event_bus = event_bus
        self.cache = cache
        self.topic_name = "job_event_stream"
        # 定义 Redis Key 前缀
        self.CACHE_PREFIX = "ev:inst:"
        self.CACHE_TTL = 3600 * 24  # 缓存 24 小时，保证活跃任务都在内存

    async def _save_payload(self, payload: dict) -> str:
        """
        保存大字段到外部存储（如 OSS/S3 或 Redis）
        目前简化实现，直接返回一个模拟的 key
        """
        # 实际实现中，这里应该将 payload 保存到外部存储
        # 并返回对应的引用 key
        return f"payload-{str(uuid.uuid4())[:8]}"

    # ==========================
    #  核心：缓存读写封装
    # ==========================

    def _cache_key(self, instance_id: str) -> str:
        return f"{self.CACHE_PREFIX}{instance_id}"

    def _serialize(self, instance: EventInstance) -> dict:


        """
        使用 Pydantic 的 model_dump 进行序列化，自动处理 datetime 等类型。
        """
        return instance.model_dump(
            mode="json",  # 自动将 datetime、UUID 等转为 JSON 兼容格式（如 ISO 字符串）
            exclude_unset=False,
            exclude_defaults=False,
            # 如果某些字段不需要序列化（比如 updated_at 不用于缓存），可加 exclude={"updated_at"}
        )

    async def _get_instance_with_cache(self, session: AsyncSession, instance_id: str) -> Optional[dict]:
        """
        【读优先】：Redis -> DB -> Redis
        返回的是 Dict（如果来自 Redis）或 Object 转成的 Dict
        """
        key = self._cache_key(instance_id)

        # 1. 尝试从 Redis 读取
        cached_data = await self.cache.get(key)
        if cached_data:
            # 假设 cache.get 返回的是 json string，需要 load
            # 如果 cache 客户端自动处理了 json，这里直接返回
            return json.loads(cached_data) if isinstance(cached_data, str) else cached_data

        # 2. Redis Miss，回源查 DB
        inst_repo = create_event_instance_repo(session, dialect)
        instance = await inst_repo.get(instance_id)
        
        if not instance:
            return None

        # 3. 回写 Redis (Read Repair)
        data_dict = self._serialize(instance)
        # 异步写入，不阻塞主流程太多
        await self.cache.set(key, json.dumps(data_dict), ex=self.CACHE_TTL)

        return data_dict

    async def _update_instance_cache(self, instance_id: str, update_fields: dict, original_data: dict = None):
        """
        【写辅助】：更新 Redis 中的状态
        """
        key = self._cache_key(instance_id)
        
        # 如果没有原始数据，先查一次 Redis (或者直接覆盖，取决于业务)
        # 推荐：先 get -> merge -> set
        current_data = original_data
        if not current_data:
             raw = await self.cache.get(key)
             if raw:
                 current_data = json.loads(raw) if isinstance(raw, str) else raw
             else:
                 # 极端情况：缓存没了，不处理或仅更新现有字段
                 # 这里选择仅写入 update_fields，虽然不完整，但包含了最新状态
                 current_data = {}

        # 合并数据
        # 注意：处理 datetime 对象的序列化
        safe_updates = {}
        for k, v in update_fields.items():
            if isinstance(v, datetime):
                safe_updates[k] = v.isoformat()
            else:
                safe_updates[k] = v
        
        current_data.update(safe_updates)
        current_data["id"] = instance_id # 确保 ID 存在
        
        await self.cache.set(key, json.dumps(current_data), ex=self.CACHE_TTL)

    async def _record_event_log(self, session: AsyncSession, instance_id: str, trace_id: str, event_type: str, payload: dict, error: str = None):
        """
        【新增辅助方法】通用流水账记录
        对应执行系统的每一次“上报”
        Log 依然走 DB，因为 Log 是 Append-Only 的，通常不需要读缓存
        """
        log_repo = create_event_log_repo(session, dialect)
        log_entry = EventLog(
            id=str(uuid.uuid4()),
            instance_id=instance_id,
            trace_id=trace_id,
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
        input_params: dict,
        request_id: str,                # 【新增】必须传入 request_id 用于关联
        root_def_id: Optional[str] = None, # 【修改】变为可选，如果不传则内部生成
        trace_id: Optional[str] = None, # 【修改】变为可选，如果不传则内部生成
        user_id: Optional[str] = None   # 记录是谁触发的

    ) -> str:
        """
        启动链路
        维护 request_id (1) -> trace_id (N) 的关系
        """
        # 1. 处理root_def_id为None的情况，生成默认ID
        if root_def_id is None:
            root_def_id = f"default-{str(uuid.uuid4())[:8]}"
        
        # 2. 校验定义是否存在，不存在则创建默认定义
        def_repo = create_event_definition_repo(session, dialect)
        definition = await def_repo.get(root_def_id)
        if not definition:
            # 创建默认定义
            from common.event_definition import EventDefinition
            from common.enums import ActorType, NodeType, ScheduleType
            
            definition = EventDefinition(
                id=root_def_id,
                name=f"Default Definition for {root_def_id}",
                user_id=user_id or "system",
                node_type=NodeType.AGENT_ACTOR,
                actor_type=ActorType.AGENT,
                code_ref="default/default:latest",
                entrypoint="main.run",
                schedule_type=ScheduleType.ONCE,
                resource_profile="default",
                default_params={}
            )
            await def_repo.create(definition)

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
            user_id=user_id,
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
        
        # 立即写入 Redis，这样下一毫秒如果有查询就能命中
        await self.cache.set(
            self._cache_key(root_id),
            json.dumps(self._serialize(root)),
            ex=self.CACHE_TTL
        )
        
        # 【新增】记录 EventLog (历史轨迹)
        # 即使是创建，也应该是一条 Log，方便回溯 "什么时候开始的"
        await self._record_event_log(
            session,
            root_id,
            trace_id,
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

        # 1. 【读取优化】从缓存获取 Parent
        # 这避免了一次 DB SELECT
        parent_data = await self._get_instance_with_cache(session, parent_id)
        
        if not parent_data:
            raise ValueError(f"Parent {parent_id} not found")
        
        # 校验逻辑使用 Dict 操作
        if trace_id and parent_data['trace_id'] != trace_id:
             raise ValueError(f"Parent node {parent_id} does not belong to trace {trace_id}")
        
        if parent_data.get('control_signal') == "CANCEL":
            raise ValueError("Parent event is cancelled")

        new_instances = []
        new_ids = []
        inst_repo = create_event_instance_repo(session, dialect)
        def_repo = create_event_definition_repo(session, dialect)

        for meta in subtasks_meta:
            # 从外部输入获取id
            if "id" not in meta:
                raise ValueError(f"Missing required 'id' field in subtask meta: {meta}")
            child_id = meta["id"]
            new_ids.append(child_id)
            
            # 获取子任务定义，不存在则创建默认定义
            child_def = await def_repo.get(meta["def_id"])
            if not child_def:
                # 创建默认定义
                from common.event_definition import EventDefinition
                from common.enums import ActorType, NodeType, ScheduleType
                
                child_def = EventDefinition(
                    id=meta["def_id"],
                    name=f"Default Definition for {meta['def_id']}",
                    user_id=parent_data.get('user_id') or "system",
                    node_type=NodeType.TASK,
                    actor_type=ActorType.GENERAL,
                    code_ref="default/default:latest",
                    entrypoint="main.run",
                    schedule_type=ScheduleType.ONCE,
                    resource_profile="default",
                    default_params={}
                )
                await def_repo.create(child_def)
            
            child = EventInstance(
                id=child_id,
                trace_id=parent_data['trace_id'],
                parent_id=parent_id,
                job_id=parent_data['job_id'],
                def_id=meta["def_id"], # 必须关联到具体的 Definition
                user_id=parent_data.get('user_id'),
                
                # 【关键】构建物化路径
                node_path=f"{parent_data['node_path']}{parent_id}/",
                depth=parent_data['depth'] + 1,
                
                actor_type=child_def.actor_type,
                role=child_def.role,
                name=meta.get("name"),
                status=EventInstanceStatus.PENDING, # 初始为 PENDING，等待调度
                input_params={**child_def.default_params, **meta.get("params", {})},
                input_ref=await self._save_payload(meta.get("params", {})),
                created_at=datetime.now(timezone.utc),
                # 【修改点 3】: 状态继承 (Inheritance)
                # 关键！如果父节点有信号（比如 PAUSE），子节点必须继承。
                control_signal=parent_data.get('control_signal')
            )
            new_instances.append(child)
            
        # 2. 【写入优化】批量写入
        await inst_repo.bulk_create(new_instances)
        
        # 3. 批量回写 Redis
        for inst in new_instances:
            await self.cache.set(
                self._cache_key(inst.id),
                json.dumps(self._serialize(inst)),
                ex=self.CACHE_TTL
            )
        
        # 【新增】记录 Parent 的 EventLog
        # 记录 "我生了孩子" 这一事件
        await self._record_event_log(
            session,
            parent_id,
            parent_data['trace_id'],
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
                key=parent_data['trace_id'],
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

        # 1. 【读取优化】先从 Redis 拿，避免 SELECT
        # 这一步非常关键，高并发下数据库读压力减少 90%
        instance_data = await self._get_instance_with_cache(session, task_id)
        
        if not instance_data:
            print(f"Warning: Received event {event_type} for unknown task {task_id}")
            return

        # 2. 计算 Update Fields
        update_fields = {"updated_at": datetime.now(timezone.utc)}
        
        if event_type == "STARTED":
            update_fields["status"] = EventInstanceStatus.RUNNING.value # 注意存 String 或 Enum Value
            update_fields["started_at"] = datetime.now(timezone.utc)
        elif event_type == "COMPLETED":
            update_fields["status"] = EventInstanceStatus.SUCCESS.value
            update_fields["finished_at"] = datetime.now(timezone.utc)
            update_fields["progress"] = 100
            if data:
                update_fields["output_ref"] = str(data)
        elif event_type == "FAILED":
            update_fields["status"] = EventInstanceStatus.FAILED.value
            update_fields["finished_at"] = datetime.now(timezone.utc)
            update_fields["error_detail"] = {"msg": error_msg}
        elif event_type == "PROGRESS":
            if isinstance(data, dict) and "percent" in data:
                update_fields["progress"] = data["percent"]

        # 更新快照 (始终保持最新)
        if snapshot:
            update_fields["runtime_state_snapshot"] = snapshot

        # 3. 【写优先】更新 Redis
        # 让后续的查询立刻看到状态变更，无需等待 DB 事务提交
        await self._update_instance_cache(task_id, update_fields, original_data=instance_data)

        # 4. 【写落地】更新 DB
        # 使用 update_fields 只需要 ID，不需要 attach 整个对象，效率很高
        inst_repo = create_event_instance_repo(session, dialect)
        await inst_repo.update_fields(task_id, **update_fields)

        # 5. 记录日志 (Append Only, 直接写 DB)
        await self._record_event_log(
            session,
            task_id,
            instance_data.get('trace_id'), # 从缓存拿到的 trace_id
            event_type,
            execution_args,
            error=error_msg
        )

        # 6. 【新增逻辑】提取 Agent 身份并通过事件总线上报心跳
        agent_id = execution_args.get("agent_id")
        
        if agent_id:
            task_info = None
            
            # 如果是正在运行，记录当前任务信息
            if event_type in ["STARTED", "RUNNING", "PROGRESS"]:
                task_info = {
                    "trace_id": instance_data.get("trace_id"),
                    "task_id": task_id,
                    "name": instance_data.get("name", "Unknown Task"),
                    "step": execution_args.get("realtime_info", {}).get("step")
                }
            
            # 这里的 "Report Heartbeat" 意味着 Agent 刚刚还在说话，它是活的
            # 如果 event_type 是 FAILED 或 COMPLETED，task_info 可能是 None，表示它刚干完活，现在闲下来了(IDLE)
            await self.event_bus.publish(
                topic=self.topic_name,
                event_type="AGENT_HEARTBEAT",
                key=agent_id,
                payload={
                    "agent_id": agent_id,
                    "task_info": task_info
                }
            )

        # 7. 发送通知
        await self.event_bus.publish(
            topic=self.topic_name,
            event_type=f"TASK_{event_type}",
            key=instance_data.get('trace_id'),
            payload={
                "task_id": task_id,
                "status": update_fields.get("status"),
                "progress": update_fields.get("progress")
            }
        )

