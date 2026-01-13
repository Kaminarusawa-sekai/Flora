好的！以下是基于您任务系统（指令塔）设计的 **5 个核心 Pydantic DTO（Data Transfer Object）模型**，对应我们前面讨论的五类内部数据结构。这些模型可用于数据库 ORM 映射、MQ 消息解析、内部服务通信等场景。

------

## ✅ 五个核心 DTO（Pydantic v2 风格）

```python
# dto.py
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from pydantic import BaseModel, Field


# ===== 1. 任务定义（静态模板）=====
class TaskDefinition(BaseModel):
    id: str = Field(..., description="任务定义唯一ID，如 'web_crawl_v2'")
    name: str
    actor_type: str = Field(..., description="执行者类型：AGENT / EXECUTION / GROUP_AGG 等")
    code_ref: str = Field(..., description="执行逻辑引用，如 docker://my/agent:v1")
    default_params: Dict[str, Any] = Field(default_factory=dict)
    timeout_sec: int = 300
    max_retries: int = 3
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ===== 2. 任务实例（动态树节点）=====
class TaskInstanceStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    SKIPPED = "SKIPPED"

class ActorType(str, Enum):
    AGENT = "AGENT"
    GROUP_AGG = "GROUP_AGG"
    SINGLE_AGG = "SINGLE_AGG"
    EXECUTION = "EXECUTION"

class TaskInstance(BaseModel):
    id: str = Field(..., description="任务实例唯一ID（建议 ULID）")
    trace_id: str = Field(..., description="根任务ID，整条链路标识")
    parent_id: Optional[str] = None
    job_id: str = Field(..., description="关联的 task_definition.id")

    actor_type: ActorType
    status: TaskInstanceStatus

    node_path: str = Field(..., description="物化路径，如 '/root/child1/grandchild/'")
    depth: int = 0
    split_count: int = 0          # 计划分裂出多少子任务
    completed_children: int = 0   # 已完成的子任务数（含失败/取消）

    input_params: Dict[str, Any] = Field(default_factory=dict)
    output_ref: Optional[str] = None
    error_code: Optional[str] = None
    error_msg: Optional[str] = None

    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ===== 3. 控制事件（用户/系统发起的指令）=====
class ControlAction(str, Enum):
    RUN = "RUN"
    PAUSE = "PAUSE"
    CANCEL = "CANCEL"

class ControlEvent(BaseModel):
    id: str
    trace_id: str
    task_id: Optional[str] = None  # 若为 None，表示作用于整棵树
    action: ControlAction
    triggered_by: str = Field(..., description="user_id 或 system")
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ===== 4. 状态上报事件（Actor → MQ）=====
class TaskEventType(str, Enum):
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class TaskEvent(BaseModel):
    event_id: str = Field(..., description="全局唯一事件ID（用于去重）")
    trace_id: str
    task_id: str
    parent_id: Optional[str] = None
    actor_type: ActorType
    event_type: TaskEventType

    payload: Dict[str, Any] = Field(default_factory=dict)  # 包含 progress, message, output_ref 等
    timestamp_ms: int


# ===== 5. 聚合上下文（可选优化）=====
class AggregationContext(BaseModel):
    aggregator_task_id: str = Field(..., alias="aggregator_task_id")
    expected_children: int
    received_children: int = 0
    child_results: List[Dict[str, Any]] = Field(default_factory=list)  # 存 output_ref + status 快照
    is_ready: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        populate_by_name = True
```

> 💡 说明：
>
> - 所有 ID 建议使用 **ULID**（字典序、无冲突、含时间戳），而非 UUID。
> - `TaskEvent.payload` 是灵活字段，可包含 `progress: int`, `message: str`, `output_ref: str` 等。
> - `AggregationContext` 可按需启用，简单场景可省略。

------

## 🧪 完整运行示例：用户请求“用三种策略分析特斯拉财报”

### 步骤 1：任务定义（预置）

```python
job_def = TaskDefinition(
    id="multi_strategy_financial_analysis",
    name="多策略财报分析",
    actor_type="AGENT",
    code_ref="docker://my/financial-router:latest",
    default_params={"strategies": ["fundamental", "sentiment", "technical"]},
    timeout_sec=1800
)
# 存入 task_definitions 表
```

------

### 步骤 2：触发一次运行（生成根任务）

```python
root_task = TaskInstance(
    id="task_ulid_root_001",
    trace_id="run_ulid_xyz789",
    parent_id=None,
    job_id="multi_strategy_financial_analysis",
    actor_type=ActorType.AGENT,
    status=TaskInstanceStatus.PENDING,
    node_path="/run_ulid_xyz789/",
    depth=0,
    input_params={"target": "Tesla", "year": 2024},
    split_count=3  # Router 会分裂出 3 个策略
)
# 写入 task_instances
```

------

### 步骤 3：Agent 执行并预注册子任务

Agent 运行后，调用指令塔注册 3 个子任务：

```python
sub_tasks = [
    TaskInstance(
        id="task_ulid_stratA",
        trace_id="run_ulid_xyz789",
        parent_id="task_ulid_root_001",
        job_id="strategy_fundamental",  # 不同的 job_id！
        actor_type=ActorType.EXECUTION,
        status=TaskInstanceStatus.PENDING,
        node_path="/run_ulid_xyz789/task_ulid_stratA/",
        depth=1,
        input_params={"target": "Tesla", "method": "fundamental"}
    ),
    # ... 同理 stratB (sentiment), stratC (technical)
]
# 全部写入 task_instances
```

此时 DB 中已有 4 条记录，构成一棵树。

------

### 步骤 4：子任务执行并上报事件

```python
event1 = TaskEvent(
    event_id="evt_ulid_abc123",
    trace_id="run_ulid_xyz789",
    task_id="task_ulid_stratA",
    parent_id="task_ulid_root_001",
    actor_type=ActorType.EXECUTION,
    event_type=TaskEventType.STARTED,
    payload={"message": "开始基本面分析..."},
    timestamp_ms=1734567890123
)

event2 = TaskEvent(
    event_id="evt_ulid_def456",
    trace_id="run_ulid_xyz789",
    task_id="task_ulid_stratA",
    event_type=TaskEventType.COMPLETED,
    payload={
        "output_ref": "s3://results/fundamental_tesla_2024.json",
        "score": 0.87
    },
    timestamp_ms=1734567950000
)
# 发送到 MQ: tms.task.events
```

------

### 步骤 5：用户中途取消

```python
cancel_cmd = ControlEvent(
    id="ctrl_ulid_cancel_001",
    trace_id="run_ulid_xyz789",
    action=ControlAction.CANCEL,
    triggered_by="user_123"
)
# 指令塔：
# 1. 写入 Redis: HSET cmd:instance:run_ulid_xyz789 global_action CANCEL
# 2. 写入 control_events 表（用于审计）
```

正在运行的 `stratB` 下次检查 Redis 时发现 `CANCEL`，主动上报：

```python
event3 = TaskEvent(
    event_id="evt_ulid_cancel_789",
    task_id="task_ulid_stratB",
    event_type=TaskEventType.CANCELLED,
    payload={"message": "被用户取消"},
    trace_id="run_ulid_xyz789",
    ...
)
```

------

### 步骤 6：指令塔内部状态最终一致

- `task_instances` 表中：
  - `task_ulid_stratA`: status=SUCCESS, finished_at=...
  - `task_ulid_stratB`: status=CANCELLED
  - `task_ulid_stratC`: 可能还是 PENDING（未启动），或也被标记 CANCELLED（后台清理）
  - `task_ulid_root_001`: completed_children=3, status=SUCCESS（假设 Aggregator 允许部分成功）
- 外部可通过 `trace_id=run_ulid_xyz789` 查询整棵树状态。

------

## ✅ 总结

这 5 个 DTO 覆盖了指令塔内部所有关键数据流：

| DTO                  | 对应实体   | 用途                     |
| -------------------- | ---------- | ------------------------ |
| `TaskDefinition`     | 任务模板   | 定义“怎么跑”             |
| `TaskInstance`       | 任务实例树 | 记录“这次跑得怎样”       |
| `ControlEvent`       | 控制日志   | 记录“谁在干预”           |
| `TaskEvent`          | 上报事件   | “Actor 告诉我发生了什么” |
| `AggregationContext` | 聚合快照   | “加速决策是否汇总”       |

您可以直接将这些模型用于 FastAPI、SQLModel、消息解析、内部服务通信等场景。

如果需要，我还可以提供：

- SQLAlchemy ORM 映射版本
- Kafka 消息序列化示例
- Task Tracker 处理 `TaskEvent` 的完整伪代码

欢迎继续深入！