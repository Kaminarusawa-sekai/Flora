
import uuid
import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

# 导入正确的模块
from common.event_instance import EventInstance
from common.enums import EventInstanceStatus,ActorType
from external.cache.base import CacheClient
from external.db.session import dialect
from external.db.impl import create_event_instance_repo
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



    # ==========================
    #  核心：缓存读写封装
    # ==========================

    def _cache_key(self, task_id: str) -> str:
        """
        【修正 1】Key 的生成必须统一。
        现在的约定是：所有的缓存查找和 DB 查找都优先基于 task_id (业务ID)，
        而不是内部的 UUID。确保 task_id 全局唯一或在 Trace 内唯一。
        """
        if not task_id:
            raise ValueError("task_id cannot be None for cache key")
        return f"{self.CACHE_PREFIX}{task_id}"

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

    async def _get_instance_with_cache(self, session: AsyncSession, task_id: str) -> Optional[dict]:
        """
        【读优先】：Redis -> DB -> Redis
        返回的是 Dict（如果来自 Redis）或 Object 转成的 Dict
        【修正 2】使用仓库层的 get_by_task_id 方法查询 DB
        """
        key = self._cache_key(task_id)

        # 1. 尝试从 Redis 读取
        cached_data = await self.cache.get(key)
        if cached_data:
            # 假设 cache.get 返回的是 json string，需要 load
            # 如果 cache 客户端自动处理了 json，这里直接返回
            return json.loads(cached_data) if isinstance(cached_data, str) else cached_data

        # 2. Redis Miss，回源查 DB (使用 task_id 查询)
        inst_repo = create_event_instance_repo(session, dialect)
        instance = await inst_repo.get_by_task_id(task_id)
        
        if not instance:
            return None

        # 3. 回写 Redis (Read Repair)
        data_dict = self._serialize(instance)
        # 异步写入，不阻塞主流程太多
        await self.cache.set(key, json.dumps(data_dict), ex=self.CACHE_TTL)

        return data_dict

    async def _update_instance_cache(self, task_id: str, update_fields: dict, original_data: dict = None):
        """
        【写辅助】：更新 Redis 中的状态
        【修正 3】如果缓存完全丢失，这里不应该初始化为空字典，
        最好是触发一次 DB 重载，或者只记录 update_fields（风险是丢失旧字段）
        这里的策略是：如果没有 original，且缓存也没了，暂时仅存储更新字段，
        但实际上 _get_instance_with_cache 应该在 update 前被调用过。
        """
        key = self._cache_key(task_id)
        
        current_data = original_data
        if not current_data:
             raw = await self.cache.get(key)
             if raw:
                 current_data = json.loads(raw) if isinstance(raw, str) else raw
             else:
                 # 极端情况：缓存没了，不处理或仅更新现有字段
                 # 这里选择仅写入 update_fields，虽然不完整，但包含了最新状态
                 current_data = {"task_id": task_id} # 至少保证 task_id 存在

        # 合并数据
        # 注意：处理 datetime 对象的序列化
        safe_updates = {}
        for k, v in update_fields.items():
            if isinstance(v, datetime):
                safe_updates[k] = v.isoformat()
            else:
                safe_updates[k] = v
        
        current_data.update(safe_updates)
        current_data["task_id"] = task_id # 确保 task_id 存在
        
        await self.cache.set(key, json.dumps(current_data), ex=self.CACHE_TTL)

    async def _create_log_entry(
        self,
        session: AsyncSession,
        instance_id: str,
        trace_id: str,
        event_type: str,
        **kwargs
    ):
        """
        通用写流水方法，适配 EventLogDB
        """
        from external.db.models import EventLogDB
        
        log = EventLogDB(
            id=str(uuid.uuid4()),
            instance_id=instance_id,
            trace_id=trace_id,
            event_type=event_type,
            level=kwargs.get("level", "INFO"),
            content=kwargs.get("content"),
            payload_snapshot=kwargs.get("payload_snapshot"),
            execution_node=kwargs.get("execution_node"),
            agent_id=kwargs.get("agent_id"),
            error_detail=kwargs.get("error_detail"),
            created_at=datetime.now(timezone.utc)
        )
        session.add(log)
        # 注意：这里不 flush，依赖外层统一 commit，保证 Log 和 Instance 更新在同一事务

    async def start_trace(
        self,
        session: AsyncSession,
        input_params: dict,
        request_id: str,                # 【新增】必须传入 request_id 用于关联
        trace_id: str,                  # 【修改】变为必填，由外部生成

        user_id: Optional[str] = None   # 记录是谁触发的

    ) -> str:
        """
        启动链路
        维护 request_id (1) -> trace_id (N) 的关系
        """
        from external.db.models import EventTraceDB
        
        # 1. 创建 EventTrace 记录
        trace = EventTraceDB(
            trace_id=trace_id,
            request_id=request_id,
            status="RUNNING",
            user_id=user_id or "system",
            input_params=input_params
        )
        
        # 2. 直接写入数据库，不使用repo层，因为是新增表
        session.add(trace)
        await session.flush()

        # 3. 创建根节点 (def_id 可选)
        root_id = str(uuid.uuid4())
        # 【修正 4】Root 节点的 task_id 必须唯一。
        # 原代码是固定的 "init_task"，并发时会有问题。
        # 建议：使用 trace_id 作为 root 的 task_id，或者特定前缀
        root_task_id = f"root_{trace_id}"
        
        root = EventInstance(
            id=root_id,
            task_id=root_task_id,          # 【新增】传入唯一的 task_id
            trace_id=trace_id,
            request_id=request_id,   # 【新增】关键：将 request_id 写入根节点
            parent_id=None,
            def_id=None,             # 变为可选
            user_id=user_id,
            node_path="/",  # 根路径
            depth=0,
            actor_type=ActorType.AGENT,  # 直接设置默认值
            role=None,
            status=EventInstanceStatus.PENDING, # 根节点直接开始
            input_params=input_params,
            # 【移除】抽离大字段存储，直接使用 payload_snapshot 记录
            runtime_state_snapshot={"lifecycle": "created"},
            created_at=datetime.now(timezone.utc),
            name="Ready",
        )
        
        inst_repo = create_event_instance_repo(session, dialect)
        await inst_repo.create(root)
        
        # 立即写入 Redis，这样下一毫秒如果有查询就能命中
        # 【修正 5】写入 Redis 时，Key 使用 task_id (root_task_id)，而不是 UUID
        # 这样后续根据 task_id 查找才能命中
        await self.cache.set(
            self._cache_key(root_task_id),
            json.dumps(self._serialize(root)),
            ex=self.CACHE_TTL
        )
        
        # 【新增】记录 EventLog (历史轨迹)
        # 即使是创建，也应该是一条 Log，方便回溯 "什么时候开始的"
        await self._create_log_entry(
            session,
            instance_id=root_id,
            trace_id=trace_id,
            event_type="TRACE_STARTED",
            content=f"Root task started by {user_id or 'system'}",
            payload_snapshot={
                "input_params": input_params,
                "request_id": request_id
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
                "root_task_id": root_task_id, # 传递给前端/下游
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
        from external.db.models import EventInstanceDB
        
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
        new_task_ids = []
        inst_repo = create_event_instance_repo(session, dialect)

        for meta in subtasks_meta:
            # 从外部输入获取id
            if "id" not in meta:
                raise ValueError(f"Missing required 'id' field in subtask meta: {meta}")
            child_task_id = meta["id"]
            new_task_ids.append(child_task_id)
            
            # 【修正 6】显式生成 UUID
            # 这样在 bulk_create 之前我们就有了 PK，可以放心的存缓存
            child_uuid = str(uuid.uuid4())
            
            # 直接使用meta中的信息，不再强制要求def_id
            child_def_id = meta.get("def_id")
            
            # 构建子节点
            child = EventInstance(
                id=child_uuid,         # 显式赋值 UUID
                task_id=child_task_id,
                trace_id=parent_data['trace_id'],
                parent_id=parent_data.get('task_id'), # 必须存 Parent 的 UUID
                def_id=child_def_id,  # 可选
                user_id=parent_data.get('user_id'),
                
                # 【关键】构建物化路径
                node_path=f"{parent_data['node_path']}{parent_data.get('task_id')}/",
                depth=parent_data['depth'] + 1,
                
                name=meta.get("name", "Dynamic Task"),
                actor_type=ActorType(meta.get("actor_type", "AGENT")),  # 从meta获取或使用默认值，转换为枚举
                role=meta.get("role"),
                status=EventInstanceStatus.PENDING, # 初始为 PENDING，等待调度
                input_params=meta.get("params", {}),  # 直接使用meta中的params
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
            # 【修正 7】Cache Key 使用 task_id
            await self.cache.set(
                self._cache_key(inst.task_id),
                json.dumps(self._serialize(inst)),
                ex=self.CACHE_TTL
            )
        
        # 【新增】记录 Parent 的 EventLog
        # 记录 "我生了孩子" 这一事件
        await self._create_log_entry(
            session,
            instance_id=parent_data.get('id'),
            trace_id=parent_data['trace_id'],
            event_type="TOPOLOGY_EXPANDED",
            content=f"Spawned {len(new_instances)} subtasks",
            payload_snapshot={
                "children_ids": new_task_ids,
                "meta_preview": str(subtasks_meta)[:200]
            }
        )
        
        # 【使用抽象】发送 TOPOLOGY_EXPANDED 事件
        # 告诉外界：parent_id 下面裂变出了 new_task_ids 这些新任务
        if new_task_ids:
            await self.event_bus.publish(
                topic=self.topic_name,
                event_type="TOPOLOGY_EXPANDED",
                key=parent_data['trace_id'],
                payload={
                    "parent_id": parent_data.get('id'),
                    "new_instance_ids": new_task_ids,
                    "count": len(new_task_ids)
                }
            )
        
        return new_task_ids

    # ------------------------------------------------------
    # 场景3：【核心新增】同步执行状态 (对接执行系统的 Args)
    # ------------------------------------------------------
    async def sync_execution_state(
        self,
        session: AsyncSession,
        execution_args: dict
    ):
        """
        【核心方法】接收 Worker 汇报 -> 记流水 -> 更新状态
        execution_args 包含: task_id, event_type, data, error, worker_id, agent_id...
        """
        task_id = execution_args.get("task_id")
        event_type = execution_args.get("event_type")
        trace_id = execution_args.get("trace_id") # 最好由 Worker 透传，否则要查
        
        # =========================================
        # 0. 防御性检查：如果没有 trace_id，几乎无法挽救
        # =========================================
        if not trace_id:
            # 尝试最后一次努力：查缓存（虽然此时还没创建，但万一有其他并发？）
            instance_cache = await self._get_instance_with_cache(session, task_id)
            trace_id = instance_cache.get('trace_id') if instance_cache else None
            if not trace_id:
                print(f"CRITICAL: Task {task_id} has no trace_id and not found in DB.")
                return

        # =========================================
        # B. 第一步：状态投影 (State Projection)
        # 根据事件类型，计算 Instance 应该变成什么样
        # =========================================
        update_fields = {"updated_at": datetime.now(timezone.utc)}
        
        # 提取常用字段
        if "worker_id" in execution_args:
            update_fields["worker_id"] = execution_args["worker_id"]
            
        if event_type == "STARTED":
            update_fields["status"] = EventInstanceStatus.RUNNING.value
            update_fields["started_at"] = datetime.now(timezone.utc)
            
        elif event_type == "COMPLETED":
            update_fields["status"] = EventInstanceStatus.SUCCESS.value
            update_fields["finished_at"] = datetime.now(timezone.utc)
            update_fields["progress"] = 100
            # 结果可以只存引用，或者存简略信息
            if execution_args.get("data"):
                 # 假设 instance 表有个 result 字段，或者存入 output_payload
                pass

        elif event_type == "FAILED":
            update_fields["status"] = EventInstanceStatus.FAILED.value
            update_fields["finished_at"] = datetime.now(timezone.utc)
            update_fields["error_detail"] = {"msg": execution_args.get("error")} if execution_args.get("error") else None

        elif event_type == "PROGRESS":
            data = execution_args.get("data", {})
            if isinstance(data, dict) and "percent" in data:
                update_fields["progress"] = data["percent"]

        # 更新 Instance 快照字段 (如果有)
        if "enriched_context_snapshot" in execution_args:
             update_fields["runtime_state_snapshot"] = execution_args["enriched_context_snapshot"]

        # =========================================
        # C. 第二步：执行 UPDATE 或 UPSERT
        # 现在使用封装好的 upsert_by_task_id 方法
        # =========================================
        # 创建仓库实例
        inst_repo = create_event_instance_repo(session, dialect)
        
        # 执行 upsert 操作，返回实例 ID
        instance_uuid = await inst_repo.upsert_by_task_id(
            task_id=task_id,
            trace_id=trace_id,
            **update_fields
        )
        await session.flush()
        # 确保 instance_cache 有值（用于后续日志和缓存更新）
        instance_cache = await self._get_instance_with_cache(session, task_id)
        if not instance_cache:
            # 如果缓存没命中，说明是新建的实例，需要手动构建缓存数据
            # 使用仓库层的 get 方法获取实例
            instance = await inst_repo.get(instance_uuid)
            
            # 构建缓存数据
            instance_cache = {
                "id": instance.id,
                "task_id": instance.task_id,
                "trace_id": instance.trace_id,
                "parent_id": instance.parent_id,
                "node_path": instance.node_path,
                "depth": instance.depth,
                "actor_type": instance.actor_type.value if hasattr(instance.actor_type, 'value') else instance.actor_type,
                "def_id": instance.def_id,
                "name": instance.name,
                "status": instance.status.value if hasattr(instance.status, 'value') else instance.status,
                "created_at": instance.created_at.isoformat() if instance.created_at else None,
                "started_at": instance.started_at.isoformat() if instance.started_at else None,
                "finished_at": instance.finished_at.isoformat() if instance.finished_at else None,
                "updated_at": instance.updated_at.isoformat() if instance.updated_at else None,
                "user_id": instance.user_id,
                "input_params": instance.input_params,
                "worker_id": instance.worker_id,
                "progress": instance.progress
            }

        # =========================================
        # A. 第三步：记流水 (Event Log)
        # 这是“发生过什么”的绝对事实
        # =========================================
        error_info = None
        if execution_args.get("error"):
            error_info = {"msg": execution_args.get("error")}
            
        await self._create_log_entry(
            session,
            instance_id=instance_uuid, # Log 关联内部 UUID
            trace_id=trace_id,
            event_type=event_type,
            level="ERROR" if error_info else "INFO",
            content=execution_args.get("description", f"State change: {event_type}"),
            # 将大字段放入 payload_snapshot
            payload_snapshot=execution_args.get("enriched_context_snapshot") or execution_args.get("data"),
            execution_node=execution_args.get("worker_id"), # 映射 worker
            agent_id=execution_args.get("agent_id"),        # 映射 agent
            error_detail=error_info
        )

        # =========================================
        # E. 第四步：更新缓存 & 推送通知 (Side Effects)
        # =========================================

        # 1. 更新 Redis 缓存
        await self._update_instance_cache(task_id, update_fields, original_data=instance_cache)

        # -------------------------------------------------------
        # [通用准备] 提前准备好通用数据 (时间、名称)，供心跳和事件使用
        # -------------------------------------------------------
        # A. 准备 Task Name (优先查缓存，因为那是最初定义的；其次查当前传入)
        task_name = "Unknown Task"
        if instance_cache and instance_cache.get("name"):
            task_name = instance_cache.get("name")
        elif execution_args.get("name"):
            task_name = execution_args.get("name")

        # B. 准备时间数据 (Start/End/Duration)
        end_time_obj = datetime.now(timezone.utc)
        start_time_obj = None
        
        # 尝试从缓存获取开始时间（这是最准确的）
        if instance_cache and instance_cache.get("started_at"):
            raw_start = instance_cache["started_at"]
            if isinstance(raw_start, str):
                try:
                    start_time_obj = datetime.fromisoformat(raw_start)
                except ValueError:
                    pass
            elif isinstance(raw_start, datetime):
                start_time_obj = raw_start
        
        # 如果缓存没有（比如刚启动），尝试从当前更新字段拿
        if not start_time_obj and update_fields.get("started_at"):
            start_time_obj = update_fields["started_at"]

        # 计算耗时
        duration_ms = 0
        if start_time_obj:
            if start_time_obj.tzinfo is None:
                start_time_obj = start_time_obj.replace(tzinfo=timezone.utc)
            duration_ms = int((end_time_obj - start_time_obj).total_seconds() * 1000)

        # -------------------------------------------------------
        # [修正 1] Heartbeat 推送：增加 task_info 嵌套结构 + 补全字段
        # -------------------------------------------------------
        # 只有这些状态才代表 Agent 在忙，需要心跳
        if execution_args.get("agent_id") and event_type in ["STARTED", "RUNNING", "PROGRESS"]:
             await self.event_bus.publish(
                topic=self.topic_name,
                event_type="AGENT_HEARTBEAT",
                key=execution_args["agent_id"],
                payload={
                    "agent_id": execution_args["agent_id"],
                    # 必须嵌套 task_info
                    "task_info": {
                        "task_id": task_id,
                        "trace_id": trace_id,  # [新增] 补全 trace_id，方便前端跳转
                        "name": task_name,     # [新增] 补全 name，Monitor重启也能知道名字
                        "status": update_fields.get("status", "RUNNING"),
                        "progress": update_fields.get("progress", 0),
                        "started_at": start_time_obj.timestamp() if start_time_obj else None # 建议转成 timestamp 或 ISO
                    }
                }
            )

        # -------------------------------------------------------
        # [修正 2] 任务状态变更推送：Task Event
        # -------------------------------------------------------
        payload = {
            "task_id": task_id,
            "event_type": event_type,
            "status": update_fields.get("status"),
            "progress": update_fields.get("progress"),
            "agent_id": execution_args.get("agent_id"),
            "trace_id": trace_id,
            "task_name": task_name, # 使用前面提取好的名字
            
            # 归档关键字段
            "start_time": start_time_obj.isoformat() if start_time_obj else None,
            "end_time": end_time_obj.isoformat(),
            "duration_ms": duration_ms,
            "result": execution_args.get("data"),
            "error_msg": execution_args.get("error")
        }

        await self.event_bus.publish(
            topic=self.topic_name,
            event_type=f"TASK_{event_type}",
            key=trace_id,
            payload=payload
        )

