from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ActorType(str, Enum):
    """
    执行器类型枚举，定义了系统中所有可能的执行器类型
    """
    # 通用任务处理器（可递归）
    AGENT = "AGENT"
    
    # 聚合层
    GROUP_AGGREGATOR = "GROUP_AGG"   # 聚合一组 SingleAgg
    SINGLE_AGGREGATOR = "SINGLE_AGG" # 聚合一个任务的多次执行/多源
    
    # 叶子执行器
    EXECUTION = "EXECUTION"


class ActorReferenceDto:
    """
    执行器引用数据传输对象
    用于在事件中传递执行器的引用信息
    """
    def __init__(
        self,
        actor_id: str,
        actor_type: ActorType,
        actor_name: Optional[str] = None,
        actor_metadata: Optional[Dict[str, Any]] = None
    ):
        self.actor_id = actor_id
        self.actor_type = actor_type
        self.actor_name = actor_name
        self.actor_metadata = actor_metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        """
        return {
            "actor_id": self.actor_id,
            "actor_type": self.actor_type.value,
            "actor_name": self.actor_name,
            "actor_metadata": self.actor_metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActorReferenceDto":
        """
        从字典创建实例
        """
        return cls(
            actor_id=data["actor_id"],
            actor_type=ActorType(data["actor_type"]),
            actor_name=data.get("actor_name"),
            actor_metadata=data.get("actor_metadata")
        )


class ActorEventDto:
    """
    执行器事件数据传输对象
    用于封装与执行器相关的事件信息
    """
    def __init__(
        self,
        event_id: str,
        event_type: str,
        timestamp: float,
        actor: ActorReferenceDto,
        payload: Optional[Dict[str, Any]] = None,
        parent_event_id: Optional[str] = None
    ):
        self.event_id = event_id
        self.event_type = event_type
        self.timestamp = timestamp
        self.actor = actor
        self.payload = payload or {}
        self.parent_event_id = parent_event_id

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        """
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "actor": self.actor.to_dict(),
            "payload": self.payload,
            "parent_event_id": self.parent_event_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActorEventDto":
        """
        从字典创建实例
        """
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            timestamp=data["timestamp"],
            actor=ActorReferenceDto.from_dict(data["actor"]),
            payload=data.get("payload"),
            parent_event_id=data.get("parent_event_id")
        )


class ActorStatus(str, Enum):
    """
    执行器状态枚举
    """
    CREATED = "CREATED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    PAUSED = "PAUSED"
    CANCELLED = "CANCELLED"


class ActorStatusDto:
    """
    执行器状态数据传输对象
    """
    def __init__(
        self,
        actor_id: str,
        status: ActorStatus,
        timestamp: float,
        message: Optional[str] = None,
        progress: Optional[float] = None,
        result: Optional[Any] = None
    ):
        self.actor_id = actor_id
        self.status = status
        self.timestamp = timestamp
        self.message = message
        self.progress = progress
        self.result = result

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        """
        return {
            "actor_id": self.actor_id,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "message": self.message,
            "progress": self.progress,
            "result": self.result
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActorStatusDto":
        """
        从字典创建实例
        """
        return cls(
            actor_id=data["actor_id"],
            status=ActorStatus(data["status"]),
            timestamp=data["timestamp"],
            message=data.get("message"),
            progress=data.get("progress"),
            result=data.get("result")
        )


class ScheduledRun(BaseModel):
    """
    定时运行记录数据传输对象
    """
    id: str
    definition_id: str
    trace_id: str
    scheduled_at: datetime
    triggered_at: Optional[datetime] = None
    status: str  # SUCCESS / FAILED


class LoopRoundContext(BaseModel):
    """
    循环轮次上下文数据传输对象
    """
    trace_id: str
    round_index: int
    input_params: Dict[str, Any]
    output_summary: Optional[Dict[str, Any]] = None
    should_continue: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
