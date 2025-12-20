from typing import Literal, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from ..external.cache.base import CacheClient
from ..external.db.session import dialect
from ..external.db.impl import create_event_instance_repo


class SignalService:
    def __init__(self, cache: CacheClient):
        self.cache = cache
    
    def _get_cache_key(self, trace_id: str) -> str:
        """获取缓存键，确保与 LifecycleService 保持一致"""
        return f"trace_signal:{trace_id}"

    async def send_signal(
        self,
        session: AsyncSession,
        trace_id: str = None,
        instance_id: str = None,
        signal: str = "CANCEL"
    ) -> None:
        """
        发送控制信号，支持两种模式：
        1. 整个 trace 控制：当 instance_id 为 None 时，向整个 trace 发送信号
        2. 级联控制：当提供 instance_id 时，向该节点及其所有子孙发送信号
        
        Args:
            session: 数据库会话
            trace_id: 跟踪ID（整个trace控制时必填）
            instance_id: 节点ID（级联控制时必填）
            signal: 控制信号，默认为 CANCEL
        """
        # 动态创建 repo 实例
        inst_repo = create_event_instance_repo(session, dialect)
        
        if instance_id:
            # 模式1：级联控制 - 向节点及其所有子孙发送信号
            # 1. 获取当前节点信息，用于校验和后续级联更新
            current_node = await inst_repo.get(instance_id)
            if not current_node:
                raise ValueError(f"Instance {instance_id} not found")
            
            # 【新增校验】确保 instance 属于指定的 trace_id
            if trace_id and current_node.trace_id != trace_id:
                raise ValueError(f"Instance {instance_id} does not belong to trace {trace_id}")
            
            # 2. 更新当前节点
            await inst_repo.update(instance_id, {"control_signal": signal})
            
            trace_id = current_node.trace_id
            
            # 3. 【级联更新】利用 node_path 快速更新所有子孙
            path_pattern = f"{current_node.node_path}{current_node.id}/%"
            await inst_repo.bulk_update_signal_by_path(
                trace_id=trace_id,
                path_pattern=path_pattern,
                signal=signal
            )
        else:
            # 模式2：整个 trace 控制 - 向整个 trace 发送信号
            if not trace_id:
                raise ValueError("Either trace_id or instance_id must be provided")
            
            # 更新该 trace 下所有任务的信号
            await inst_repo.update_signal_by_trace(
                trace_id,
                signal=signal
            )
        
        # 4. 同时发送缓存信号
        cache_key = self._get_cache_key(trace_id)
        await self.cache.set(cache_key, signal, ttl=3600)
    
    # 兼容旧接口
    async def cancel_trace(self, session: AsyncSession, trace_id: str):
        """取消跟踪（兼容旧版接口）"""
        await self.send_signal(session, trace_id=trace_id, signal="CANCEL")
    
    async def stop_trace(self, session: AsyncSession, trace_id: str):
        """
        [远程遥控]
        将整个链路标记为 CANCEL。
        """
        await self.send_signal(session, trace_id=trace_id, signal="CANCEL")

    async def check_signal(self, trace_id: str, session: Optional[AsyncSession] = None) -> Optional[str]:
        """供内部服务调用（如调度器预检）"""
        key = self._get_cache_key(trace_id)
        signal = await self.cache.get(key)
        
        if signal is not None:
            return signal
        
        # 降级：查数据库（避免 Redis 故障导致无法取消）
        if session:
            try:
                # 使用现有的 repo 创建方法，避免循环依赖
                inst_repo = create_event_instance_repo(session, dialect)
                # 查询该 trace 下的所有实例，获取最新的信号
                instances = await inst_repo.find_by_trace_id(trace_id)
                if instances:
                    # 从实例中提取信号，优先使用非空信号
                    for instance in instances:
                        if instance.control_signal:
                            signal = instance.control_signal
                            break
                    if signal:
                        await self.cache.set(key, signal, ttl=3600)  # 回填缓存
                        return signal
            except Exception as e:
                # 避免数据库查询失败导致整个方法出错
                pass
        
        return None

    async def check_trace_signal(self, trace_id: str) -> bool:
        """检查跟踪是否被取消（兼容旧版接口）"""
        signal = await self.check_signal(trace_id)
        return signal == "CANCEL"
