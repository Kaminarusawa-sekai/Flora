from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text, Index
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class TaskDefinitionDB(Base):
    __tablename__ = "task_definitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    content = Column(JSON, nullable=False, default={})
    cron_expr = Column(String, nullable=True)  # 例如 "*/5 * * * *"
    schedule_type = Column(String, nullable=False, default="IMMEDIATE")
    schedule_config = Column(JSON, default={})
    # 存储循环配置，例如 {"max_rounds": 5, "interval_sec": 10}
    loop_config = Column(JSON, default={})
    is_active = Column(Boolean, default=True)
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_temporary = Column(Boolean, default=False)

class TaskInstanceDB(Base):
    __tablename__ = "task_instances"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    definition_id = Column(String, nullable=False) # 关联 Definition
    trace_id = Column(String, index=True)          # 全链路追踪 ID
    
    status = Column(String, default="PENDING")     # PENDING, RUNNING, SUCCESS, FAILED
    
    # 调度相关
    schedule_type = Column(String, default="ONCE") # CRON, LOOP, ONCE
    round_index = Column(Integer, default=0)       # 当前是循环的第几轮
    
    # 依赖管理 (DAG)
    depends_on = Column(JSON, default=[])          # ["task-id-1", "task-id-2"]
    
    # 运行参数与结果
    input_params = Column(JSON, default={})
    output_ref = Column(String, nullable=True)     # 结果存储地址
    error_msg = Column(Text, nullable=True)
    
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))


class ScheduledTaskDB(Base):
    __tablename__ = "scheduled_tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    definition_id = Column(String, nullable=False, index=True)
    trace_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, default="PENDING")
    
    # 调度相关
    schedule_type = Column(String, nullable=False, default="IMMEDIATE")
    scheduled_time = Column(DateTime(timezone=True), nullable=False, index=True)
    execute_after = Column(DateTime(timezone=True), index=True)
    schedule_config = Column(JSON, default={})
    
    # 执行相关
    round_index = Column(Integer, default=0)
    input_params = Column(JSON, default={})
    output_ref = Column(String, nullable=True)
    error_msg = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    depends_on = Column(JSON, default=[])  # 存储为JSON数组
    
    # 调度控制
    priority = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    retry_count = Column(Integer, default=0)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    external_status_pushed = Column(Boolean, default=False)
    
    # 索引
    __table_args__ = (
        Index('idx_scheduled_tasks_status_scheduled_time', 'status', 'scheduled_time'),
        Index('idx_scheduled_tasks_trace_id', 'trace_id'),
        {'extend_existing': True}
    )
