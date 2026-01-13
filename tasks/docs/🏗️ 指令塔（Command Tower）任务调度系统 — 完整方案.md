

------

# 🏗️ 指令塔（Command Tower）任务调度系统 — 完整方案

> **目标**：支持智能体工作流（Agent Workflow），具备：
>
> - 递归裂变（Layered Execution）
> - DAG 依赖调度（depends_on）
> - 原生 CRON（多 trace）与 LOOP（单 trace 多轮）
> - 全局信号控制（按 trace_id 取消）
> - 高效状态查询与进度上报

------

## 一、项目结构（Python + Async + Pydantic）

```
command_tower/

├── common/                # L1: 领域模型（纯 DTO）
│   ├── __init__.py
│   ├── enums.py
│   ├── task_definition.py
│   └── task_instance.py
│
├── external/                 # L2: 基础设施抽象与实现
│   ├── db/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── models.py       # SQLAlchemy ORM
│   │   └── sqlalchemy_impl.py
│   ├── cache/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   └── redis_impl.py
│   └── messaging/
│      ├── __init__.py
│      ├── base.py
│      └── rabbitmq_delayed.py
│   │
├── services/           # L3: 应用服务（Use Case）
├── __init__.py
│   ├── lifecycle_service.py
│   ├── signal_service.py
│   └── observer_service.py
│
├── drivers/               # L4: 驱动层（入口）
│   ├── schedulers/
│   │   ├── cron_generator.py
│   │   ├── dispatcher.py
│   │   └── loop_controller.py  # 可选，由 LifecycleService 内部处理
│   
├── apps/ 
│   ├── api/
│   │   │   ├── v1/
│   │   │   │   ├── commands.py
│   │   │   │   └── queries.py
│   │   │   └── __init__.py
│   │   └── worker_client.py    # 模拟 Worker 上报
│   │
└── main.py                # 启动入口
│
├── config/
│   └── settings.py            # 配置管理
│
├── requirements.txt
└── docker-compose.yml         # 含 RabbitMQ（带延时插件）、Redis、PostgreSQL
```

------

## 二、L1：领域模型（Domain Models）

### `common/enums.py`

```python
from enum import Enum

class ActorType(str, Enum):
    AGENT = "AGENT"
    GROUP_AGG = "GROUP_AGG"
    SINGLE_AGG = "SINGLE_AGG"
    EXECUTION = "EXECUTION"

class ScheduleType(str, Enum):
    ONCE = "ONCE"
    CRON = "CRON"
    LOOP = "LOOP"

class TaskInstanceStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"
```

### `common/task_definition.py`

```python
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .enums import ActorType, ScheduleType

class TaskDefinition(BaseModel):
    id: str = Field(..., description="任务定义唯一ID")
    name: str
    actor_type: ActorType
    role: Optional[str] = None
    code_ref: str = Field(..., description="如 docker://my/agent:v1")
    entrypoint: str = "main.run"

    schedule_type: ScheduleType = ScheduleType.ONCE
    cron_expr: Optional[str] = None
    loop_config: Optional[Dict[str, Any]] = None

    resource_profile: str = "default"
    strategy_tags: List[str] = Field(default_factory=list)

    default_params: Dict[str, Any] = Field(default_factory=dict)
    timeout_sec: int = 300
    max_retries: int = 3
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
```

### `common/task_instance.py`

```python
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from .enums import ActorType, ScheduleType, TaskInstanceStatus

class TaskInstance(BaseModel):
    id: str
    trace_id: str
    parent_id: Optional[str] = None
    job_id: str

    actor_type: ActorType
    role: Optional[str] = None
    layer: int = 0
    is_leaf_agent: bool = False

    schedule_type: ScheduleType = ScheduleType.ONCE
    round_index: Optional[int] = None
    cron_trigger_time: Optional[datetime] = None

    status: TaskInstanceStatus
    node_path: str
    depth: int = 0
    depends_on: Optional[List[str]] = None

    split_count: int = 0
    completed_children: int = 0

    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_ref: Optional[str] = None
    error_msg: Optional[str] = None

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
```

------

## 三、L2：基础设施层（Infra）

### `external/db/base.py`

```python
from abc import ABC
from typing import List, Optional
from app.domain.task_instance import TaskInstance
from app.domain.task_definition import TaskDefinition

class TaskDefinitionRepository(ABC):
    async def get(self, def_id: str) -> TaskDefinition: ...
    async def list_active_cron(self) -> List[TaskDefinition]: ...

class TaskInstanceRepository(ABC):
    async def create(self, instance: TaskInstance) -> None: ...
    async def get(self, instance_id: str) -> TaskInstance: ...
    async def get_by_ids(self, ids: List[str]) -> List[TaskInstance]: ...
    async def find_by_trace_id(self, trace_id: str) -> List[TaskInstance]: ...
    async def lock_for_execution(self, instance_id: str, worker_id: str) -> bool: ...
    async def update_status(self, instance_id: str, status: TaskInstanceStatus, **kwargs) -> None: ...
    async def increment_completed_children(self, parent_id: str) -> int: ...
    async def find_ready_tasks(self) -> List[TaskInstance]: ...
    async def bulk_update_status_by_trace(self, trace_id: str, status: TaskInstanceStatus) -> None: ...
```

### `external/db/models.py`（SQLAlchemy）

```python
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class TaskInstanceDB(Base):
    __tablename__ = "task_instances"

    id = Column(String, primary_key=True)
    trace_id = Column(String, index=True)
    parent_id = Column(String, index=True)
    job_id = Column(String)

    actor_type = Column(String)
    layer = Column(Integer)
    is_leaf_agent = Column(Boolean)

    schedule_type = Column(String)
    round_index = Column(Integer, nullable=True)
    cron_trigger_time = Column(DateTime, nullable=True)

    status = Column(String, index=True)
    node_path = Column(String)
    depth = Column(Integer)
    depends_on = Column(JSON)

    split_count = Column(Integer, default=0)
    completed_children = Column(Integer, default=0)

    input_params = Column(JSON)
    output_ref = Column(String, nullable=True)
    error_msg = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

Index("idx_status_pending", TaskInstanceDB.status, postgresql_where=(TaskInstanceDB.status == 'PENDING'))
```

### `external/db/sqlalchemy_impl.py`（关键方法）

```python
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from .base import TaskInstanceRepository
from .models import TaskInstanceDB
from app.domain.task_instance import TaskInstance
from app.domain.enums import TaskInstanceStatus
import json

class SQLAlchemyTaskInstanceRepo(TaskInstanceRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def find_ready_tasks(self) -> List[TaskInstance]:
        # 查找所有 PENDING 且无依赖 or 依赖已全部完成的任务
        stmt = select(TaskInstanceDB).where(
            TaskInstanceDB.status == TaskInstanceStatus.PENDING
        )
        result = await self.session.execute(stmt)
        candidates = result.scalars().all()

        ready = []
        for t in candidates:
            if not t.depends_on:
                ready.append(t)
            else:
                dep_ids = t.depends_on
                dep_stmt = select(TaskInstanceDB.status).where(
                    TaskInstanceDB.id.in_(dep_ids)
                )
                deps = (await self.session.execute(dep_stmt)).scalars().all()
                if all(s == TaskInstanceStatus.SUCCESS for s in deps):
                    ready.append(t)
        return [self._to_domain(t) for t in ready]

    async def increment_completed_children(self, parent_id: str) -> int:
        stmt = (
            update(TaskInstanceDB)
            .where(TaskInstanceDB.id == parent_id)
            .values(completed_children=TaskInstanceDB.completed_children + 1)
            .returning(TaskInstanceDB.completed_children)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    def _to_domain(self, db: TaskInstanceDB) -> TaskInstance:
        return TaskInstance(
            id=db.id,
            trace_id=db.trace_id,
            parent_id=db.parent_id,
            job_id=db.job_id,
            actor_type=db.actor_type,
            layer=db.layer,
            is_leaf_agent=db.is_leaf_agent,
            schedule_type=db.schedule_type,
            round_index=db.round_index,
            cron_trigger_time=db.cron_trigger_time,
            status=TaskInstanceStatus(db.status),
            node_path=db.node_path,
            depth=db.depth,
            depends_on=json.loads(db.depends_on) if db.depends_on else None,
            split_count=db.split_count,
            completed_children=db.completed_children,
            input_params=json.loads(db.input_params) if db.input_params else {},
            output_ref=db.output_ref,
            error_msg=db.error_msg,
            started_at=db.started_at,
            finished_at=db.finished_at,
            created_at=db.created_at,
            updated_at=db.updated_at
        )
```

> 💡 **注意**：生产环境建议用缓存优化 `depends_on` 验证（如 Redis 存每个 task 的完成状态）。

------

## 四、L3：应用服务层（Application Services）

### `services/lifecycle_service.py`

```python
import uuid
from datetime import datetime
from app.domain.task_instance import TaskInstance
from app.domain.enums import TaskInstanceStatus, ScheduleType
from app.infra.db.base import TaskDefinitionRepository, TaskInstanceRepository
from app.infra.messaging.base import MessageBroker

class LifecycleService:
    def __init__(
        self,
        def_repo: TaskDefinitionRepository,
        inst_repo: TaskInstanceRepository,
        broker: MessageBroker
    ):
        self.def_repo = def_repo
        self.inst_repo = inst_repo
        self.broker = broker

    async def start_new_trace(
        self,
        def_id: str,
        input_params: dict,
        trigger_type: str = "MANUAL"
    ) -> str:
        definition = await self.def_repo.get(def_id)
        trace_id = str(uuid.uuid4())
        job_id = f"job-{trace_id[:8]}"
        root_id = str(uuid.uuid4())

        root = TaskInstance(
            id=root_id,
            trace_id=trace_id,
            job_id=job_id,
            parent_id=None,
            actor_type=definition.actor_type,
            role=definition.role,
            layer=0,
            is_leaf_agent=(definition.actor_type == "AGENT" and not definition.role),  # 简化判断
            schedule_type=definition.schedule_type,
            round_index=0 if definition.schedule_type == ScheduleType.LOOP else None,
            cron_trigger_time=datetime.utcnow() if definition.schedule_type == ScheduleType.CRON else None,
            status=TaskInstanceStatus.PENDING,
            node_path="/",
            input_params={**definition.default_params, **input_params},
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await self.inst_repo.create(root)
        await self._schedule_task(root)
        return trace_id

    async def handle_task_completed(self, task_id: str, output_ref: str):
        task = await self.inst_repo.get(task_id)
        await self.inst_repo.update_status(task_id, TaskInstanceStatus.SUCCESS, output_ref=output_ref, finished_at=datetime.utcnow())

        # 通知父节点
        if task.parent_id:
            new_count = await self.inst_repo.increment_completed_children(task.parent_id)
            parent = await self.inst_repo.get(task.parent_id)
            if new_count >= parent.split_count:
                await self._activate_aggregator(parent)

        # LOOP 下一轮
        if task.schedule_type == ScheduleType.LOOP:
            definition = await self.def_repo.get(task.definition_id)
            max_rounds = definition.loop_config.get("max_rounds", 1)
            current_round = task.round_index or 0
            if current_round + 1 < max_rounds:
                interval = definition.loop_config.get("interval_sec", 10)
                await self.inst_repo.update_status(
                    task_id,
                    TaskInstanceStatus.PENDING,
                    round_index=current_round + 1,
                    started_at=None,
                    finished_at=None,
                    updated_at=datetime.utcnow()
                )
                await self.broker.publish_delayed(
                    "task.execute",
                    {"instance_id": task_id},
                    delay_sec=interval
                )

    async def _activate_aggregator(self, parent: TaskInstance):
        await self.inst_repo.update_status(parent.id, TaskInstanceStatus.RUNNING, started_at=datetime.utcnow())
        await self.broker.publish("task.execute", {"instance_id": parent.id})

    async def _schedule_task(self, task: TaskInstance):
        # 即使 delay=0 也走延时队列，统一入口
        await self.broker.publish_delayed("task.execute", {"instance_id": task.id}, delay_sec=0)
```

### `services/signal_service.py`

```python
from app.infra.cache.base import CacheClient
from app.infra.db.base import TaskInstanceRepository
from app.domain.enums import TaskInstanceStatus

class SignalService:
    def __init__(self, cache: CacheClient, inst_repo: TaskInstanceRepository):
        self.cache = cache
        self.inst_repo = inst_repo

    async def cancel_trace(self, trace_id: str):
        await self.cache.set(f"trace_signal:{trace_id}", "CANCEL", ttl=3600)
        await self.inst_repo.bulk_update_status_by_trace(trace_id, TaskInstanceStatus.CANCELLED)
```

------

## 五、L4：驱动层（Drivers）

### `drivers/schedulers/dispatcher.py`

```python
import asyncio
from app.infra.messaging.base import MessageBroker
from app.infra.db.base import TaskInstanceRepository
from app.application.lifecycle_service import LifecycleService

async def task_execute_consumer(broker: MessageBroker, inst_repo: TaskInstanceRepository, worker_url: str):
    async def handler(msg: dict):
        task_id = msg["instance_id"]
        task = await inst_repo.get(task_id)

        # 检查 trace 是否被取消
        from app.infra.cache.redis_impl import redis_client
        signal = await redis_client.get(f"trace_signal:{task.trace_id}")
        if signal == "CANCEL":
            return

        # 检查依赖（DAG）
        if task.depends_on:
            deps = await inst_repo.get_by_ids(task.depends_on)
            if any(d.status != "SUCCESS" for d in deps):
                await broker.publish_delayed("task.execute", msg, 5)
                return

        # 抢锁派发
        if await inst_repo.lock_for_execution(task_id, "worker-01"):
            # 模拟调用 Worker
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(f"{worker_url}/execute", json=task.dict())

    await broker.consume("task.execute", handler)
```

### `apps/api/v1/commands.py`

```python
from fastapi import APIRouter, Body
from app.application.lifecycle_service import LifecycleService
from app.application.signal_service import SignalService

router = APIRouter()

@router.post("/traces/start")
async def start_trace(def_id: str = Body(...), params: dict = Body({})):
    trace_id = await lifecycle_svc.start_new_trace(def_id, params)
    return {"trace_id": trace_id}

@router.post("/traces/{trace_id}/cancel")
async def cancel_trace(trace_id: str):
    await signal_svc.cancel_trace(trace_id)
    return {"status": "cancelled"}
```

### `apps/api/v1/queries.py`

```python
@router.get("/traces/{trace_id}/tasks")
async def get_trace_tasks(trace_id: str, status: str = None, layer: int = None):
    tasks = await inst_repo.find_by_trace_id(trace_id)
    filtered = tasks
    if status: filtered = [t for t in filtered if t.status.value == status]
    if layer is not None: filtered = [t for t in filtered if t.layer == layer]
    return filtered
```

------

## 六、中间件配置

### `docker-compose.yml`

```yaml
version: '3.8'
services:
  rabbitmq:
    image: rabbitmq:3.12-management
    ports: ["5672:5672", "15672:15672"]
    environment:
      RABBITMQ_SERVER_ADDITIONAL_ERL_ARGS: "-rabbitmq_delayed_message_exchange true"
    volumes:
      - ./rabbitmq-delayed-plugin:/opt/rabbitmq/plugins/rabbitmq_delayed_message_exchange

  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: command_tower
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

volumes:
  pgdata:
```

> ⚠️ **RabbitMQ 延时插件**需提前下载 `.ez` 文件放入挂载目录。

------

## 七、Worker 执行协议（简版）

Worker 收到任务后：

1. 检查 `trace_signal:{trace_id}` 是否为 CANCEL

2. 执行业务逻辑

3. 若是 AGENT 且非叶子，生成子任务（调用 API `/traces/{trace_id}/split`）

4. 完成后上报：

   ```http
   POST /events
   {
     "event_type": "COMPLETED",
     "task_id": "...",
     "output_ref": "s3://result/..."
   }
   ```

------

## 八、总结：架构能力矩阵

| 能力           | 实现方式                                              |
| -------------- | ----------------------------------------------------- |
| **递归裂变**   | `layer` + `is_leaf_agent` 控制是否生成子任务          |
| **DAG 调度**   | `depends_on` + `find_ready_tasks` 依赖解析            |
| **CRON 任务**  | 每次触发新建 `trace_id`，独立生命周期                 |
| **LOOP 任务**  | 单 `trace_id` 内 `round_index` 递增，延时消息控制     |
| **全局取消**   | Redis 信号 `trace_signal:{trace_id}`，Worker 主动检查 |
| **聚合触发**   | `split_count` vs `completed_children` 计数器          |
| **高效查询**   | DB 索引（`trace_id`, `status`）+ 分页                 |
| **高并发上报** | 进度写 Redis，最终态异步持久化                        |

------

这份方案可直接用于工程落地。如需，我可提供：

- 完整 `requirements.txt`
- RabbitMQ 延时插件安装脚本
- 初始化数据库表的 Alembic 脚本
- Worker 模拟器代码

请告诉我下一步需要什么？