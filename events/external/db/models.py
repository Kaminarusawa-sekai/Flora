from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class EventDefinitionDB(Base):
    __tablename__ = "event_definitions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    
    # 核心字段：决定了前端怎么渲染，以及后端怎么处理超时/重试
    node_type = Column(String, nullable=False)
    
    actor_type = Column(String, nullable=False)
    role = Column(String, nullable=True)
    code_ref = Column(String, nullable=False)
    entrypoint = Column(String, nullable=False)
    schedule_type = Column(String, nullable=False)
    cron_expr = Column(String(100), nullable=True)
    loop_config = Column(JSON, nullable=True)
    resource_profile = Column(String, default="default")
    strategy_tags = Column(JSON, nullable=True)
    default_params = Column(JSON, nullable=True)
    
    # 策略配置
    default_timeout = Column(Integer, default=3600)
    retry_policy = Column(JSON, default=lambda: {"max_retries": 3, "backoff": "exponential"})
    
    # UI 配置：决定在拓扑图上的颜色、图标
    ui_config = Column(JSON, default=lambda: {"icon": "robot", "color": "#FF0000"})
    
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_active_cron", "is_active", "cron_expr", if_not_exists=True),
    )


class EventInstanceDB(Base):
    __tablename__ = "event_instances"

    id = Column(String, primary_key=True)
    trace_id = Column(String, index=True)
    request_id = Column(String, index=True, nullable=True)  # 关联请求ID，用于支持 request_id -> trace_id 的一对多关系
    parent_id = Column(String, index=True)
    job_id = Column(String)
    def_id = Column(String, nullable=False)  # 关联任务定义

    # 【关键优化】物化路径，格式如 "/root_id/parent_id/"
    # 添加索引以支持高效的子树查询
    node_path = Column(String, index=True)
    depth = Column(Integer)

    actor_type = Column(String)
    role = Column(String, nullable=True)
    layer = Column(Integer)
    is_leaf_agent = Column(Boolean)

    schedule_type = Column(String)
    round_index = Column(Integer, nullable=True)
    cron_trigger_time = Column(DateTime, nullable=True)

    status = Column(String, index=True)
    
    # 进度条 (0-100)
    progress = Column(Integer, default=0)
    
    # 【控制信号】
    # 指令塔写入 "PAUSE", Agent 读取并执行
    control_signal = Column(String, nullable=True)
    
    depends_on = Column(JSON)
    split_count = Column(Integer, default=0)
    completed_children = Column(Integer, default=0)

    input_params = Column(JSON)
    
    # 上下文数据引用 (不直接存大字段，存 OSS/S3 key 或 redis key)
    input_ref = Column(String, nullable=True)
    output_ref = Column(String, nullable=True)
    
    error_msg = Column(Text, nullable=True)

    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_trace_status", "trace_id", "status"),
        Index("idx_request_root", "request_id", "parent_id"),  # 支持高效查询某个请求下的根节点
    )


class EventLogDB(Base):
    __tablename__ = "event_logs"

    id = Column(String, primary_key=True)
    instance_id = Column(String, index=True, nullable=False)
    trace_id = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    level = Column(String, default="INFO")
    content = Column(Text, nullable=True)
    payload_snapshot = Column(JSON, nullable=True)
    execution_node = Column(String, nullable=True)
    agent_id = Column(String, nullable=True)
    error_detail = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_instance_id", "instance_id"),
        Index("idx_trace_id", "trace_id"),
        Index("idx_event_type", "event_type"),
    )