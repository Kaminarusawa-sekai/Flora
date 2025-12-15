from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class TaskDefinitionDB(Base):
    __tablename__ = "task_definitions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
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
    timeout_sec = Column(Integer, default=300)
    max_retries = Column(Integer, default=3)
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_active_cron", "is_active", "cron_expr"),
    )


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

    __table_args__ = (
        Index("idx_trace_status", "trace_id", "status"),
    )