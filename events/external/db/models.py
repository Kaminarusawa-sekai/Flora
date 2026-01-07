from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index, JSON, text,desc, Enum
from sqlalchemy.ext.declarative import declarative_base

from sqlalchemy.sql import func
import uuid
from common.enums import ActorType, NodeType, EventInstanceStatus

Base = declarative_base()


class EventTraceDB(Base):
    __tablename__ = "event_traces"
    
    trace_id = Column(String(64), primary_key=True)
    request_id = Column(String(64), index=True)
    status = Column(String, nullable=False)  # RUNNING / FAILED / SUCCEEDED / CANCELED
    user_id = Column(String(64), nullable=False)
    input_params = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=func.now())
    ended_at = Column(DateTime, nullable=True)
    meta = Column(JSON, nullable=True)


class EventDefinitionDB(Base):
    __tablename__ = "event_definitions"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    user_id = Column(String, nullable=False,server_default=text("''"))
    
    # 核心字段：决定了前端怎么渲染，以及后端怎么处理超时/重试
    node_type = Column(Enum(NodeType), nullable=False)
    
    actor_type = Column(Enum(ActorType), nullable=False)
    role = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class EventInstanceDB(Base):
    __tablename__ = "event_instances"

    # id = Column(String, primary_key=True)
    # 1. 内部主键 (外部不可见，用于物理存储和路径构建)
    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # 2. 外部业务ID (外部系统传进来的，如 "node_1")
    task_id = Column(String(64), nullable=False,server_default=text("'unknown_task'"))
    
    trace_id = Column(String(64), nullable=False, index=True)  # 变为必填
    request_id = Column(String(64), index=True, nullable=True)  # 关联请求ID，用于支持 request_id -> trace_id 的一对多关系
    parent_id = Column(String, index=True)
    def_id = Column(String, nullable=True)  # 变为可选
    user_id = Column(String, nullable=False,server_default=text("''"))
    worker_id = Column(String, nullable=True)  # 新增：标识当前处理该实例的worker
    name = Column(String, nullable=True)  # 新增：事件实例名称

    # 【关键优化】物化路径，格式如 "/root_id/parent_id/"
    # 添加索引以支持高效的子树查询
    node_path = Column(String, index=True)
    depth = Column(Integer, default=0)

    actor_type = Column(Enum(ActorType))
    role = Column(String, nullable=True)
    layer = Column(Integer, default=0)
    is_leaf_agent = Column(Boolean, default=False)

    status = Column(Enum(EventInstanceStatus), index=True)
    
    # 进度条 (0-100)
    progress = Column(Integer, default=0)
    
    # 【控制信号】
    # 指令塔写入 "PAUSE", Agent 读取并执行
    control_signal = Column(String, nullable=True)
    
    depends_on = Column(JSON, nullable=True)
    split_count = Column(Integer, default=0)
    completed_children = Column(Integer, default=0)

    input_params = Column(JSON, default=dict)
    
    # 上下文数据引用 (不直接存大字段，存 OSS/S3 key 或 redis key)
    input_ref = Column(String, nullable=True)
    output_ref = Column(String, nullable=True)
    
    error_detail = Column(JSON, nullable=True)  # 错误详情，支持存储更丰富的错误信息
    
    # 运行时快照，用于存储执行系统上报的最新关键上下文
    runtime_state_snapshot = Column(JSON, nullable=True)
    
    # 结果摘要，用于存储简短的返回值
    result_summary = Column(String, nullable=True)
    
    # 交互信号，Agent -> 指令塔，比如 "NEED_HUMAN_CONFIRM"
    interactive_signal = Column(String, nullable=True)

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


class AgentTaskHistory(Base):
    """
    任务履历表：记录每一次任务的详细执行情况
    对应看板功能：【历史任务明细】、【审计日志】
    """
    __tablename__ = 'agent_task_history'

    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # --- 索引字段 (查询高频) ---
    agent_id = Column(String(64), nullable=False, index=True)  # 员工ID
    trace_id = Column(String(64), nullable=False, index=True)  # 全局链路ID
    task_id = Column(String(64), nullable=False)               # 具体任务ID
    
    # --- 任务详情 ---
    task_name = Column(String(128))       # 任务名称/类型 (如 "数据清洗")
    status = Column(String(32))           # 最终状态: COMPLETED, FAILED, CANCELLED
    
    # --- 时间维度 (用于画甘特图或计算效率) ---
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    duration_ms = Column(Integer, default=0) # 执行耗时(毫秒)，直接存数值方便排序
    
    # --- 结果与上下文 ---
    # 使用 JSON 类型存储非结构化数据，适应不同 Agent 的输出
    input_params = Column(JSON, nullable=True)    # 只要是不大的参数都建议存，方便排错
    output_result = Column(JSON, nullable=True)   # 任务产出摘要
    error_msg = Column(Text, nullable=True)       # 如果 Failed，具体的报错堆栈
    
    # --- 元数据 ---
    created_at = Column(DateTime, default=func.now())

    # 联合索引建议：查询某员工最近的任务
    __table_args__ = (
        Index('idx_agent_created', 'agent_id', desc(created_at)),
    )


class AgentDailyMetric(Base):
    """
    (可选) 员工日报表：用于快速渲染看板的折线图
    """
    __tablename__ = 'agent_daily_metric'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String(64), index=True)
    date_str = Column(String(10), index=True) # yyyy-MM-dd
    
    total_tasks = Column(Integer, default=0)
    success_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    total_duration_ms = Column(Integer, default=0) # 用于计算平均耗时
    
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index('idx_agent_date', 'agent_id', 'date_str', unique=True),
    )