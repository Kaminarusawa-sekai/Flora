"""Actor引用相关的DTO定义"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ActorReferenceDTO:
    """
    Actor引用数据传输对象

    用于在系统中传递和存储Actor的引用信息
    """
    tenant_id: str
    node_id: str
    actor_address: str  # 序列化后的ActorAddress
    created_at: datetime
    expires_at: datetime
    last_heartbeat: Optional[datetime] = None

    def to_dict(self) -> dict:
        """转换为字典"""
        return {
            "tenant_id": self.tenant_id,
            "node_id": self.node_id,
            "actor_address": self.actor_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ActorReferenceDTO":
        """从字典创建"""
        from datetime import datetime

        return cls(
            tenant_id=data["tenant_id"],
            node_id=data["node_id"],
            actor_address=data["actor_address"],
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else datetime.now(),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]) if data.get("last_heartbeat") else None,
        )
