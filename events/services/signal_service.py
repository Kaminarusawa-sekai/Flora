from typing import Literal, Optional
from ..external.cache.base import CacheClient
from ..external.db.base import TaskInstanceRepository
from ..common.enums import TaskInstanceStatus


class SignalService:
    def __init__(self, cache: CacheClient, inst_repo: TaskInstanceRepository):
        self.cache = cache
        self.inst_repo = inst_repo

    async def send_signal(
        self,
        trace_id: str,
        action: Literal["CANCEL", "PAUSE"]
    ) -> None:
        """
        向指定 trace 发送控制信号。
        信号有效期 1 小时，Worker 主动轮询。
        """
        await self.cache.set(f"trace_signal:{trace_id}", action, ttl=3600)

        # 可选：立即批量更新 DB 状态（便于查询）
        if action == "CANCEL":
            await self.inst_repo.bulk_update_status_by_trace(
                trace_id, TaskInstanceStatus.CANCELLED
            )
        elif action == "PAUSE":
            await self.inst_repo.bulk_update_status_by_trace(
                trace_id, TaskInstanceStatus.PENDING
            )

    async def cancel_trace(self, trace_id: str):
        """取消跟踪（兼容旧版接口）"""
        await self.send_signal(trace_id, "CANCEL")

    async def check_signal(self, trace_id: str) -> Optional[str]:
        """供内部服务调用（如调度器预检）"""
        return await self.cache.get(f"trace_signal:{trace_id}")

    async def check_trace_signal(self, trace_id: str) -> bool:
        """检查跟踪是否被取消（兼容旧版接口）"""
        signal = await self.check_signal(trace_id)
        return signal == "CANCEL"