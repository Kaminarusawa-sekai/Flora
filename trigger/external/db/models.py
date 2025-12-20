from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Text
from sqlalchemy.orm import declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class TaskDefinitionDB(Base):
    __tablename__ = "task_definitions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    cron_expr = Column(String, nullable=True)  # 例如 "*/5 * * * *"
    is_active = Column(Boolean, default=True)
    
    # 存储循环配置，例如 {"max_rounds": 5, "interval_sec": 10}
    loop_config = Column(JSON, default={})
    
    last_triggered_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))

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
