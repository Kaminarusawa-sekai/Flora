import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from ..external.db.impl import create_task_definition_repo, create_task_instance_repo
from ..external.db.session import dialect
from ..external.messaging.base import MessageBroker


class LifecycleService:
    """任务生命周期管理服务"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
    
    async def start_new_trace(
        self,
        session: AsyncSession,
        def_id: str,
        input_params: dict,
        trigger_type: str = "CRON"
    ):
        """启动一个新的任务Trace"""
        # 1. 获取任务定义
        def_repo = create_task_definition_repo(session, dialect)
        task_def = await def_repo.get(def_id)
        
        if not task_def:
            return
        
        # 2. 生成Trace ID
        trace_id = str(uuid.uuid4())
        
        # 3. 创建任务实例
        instance_repo = create_task_instance_repo(session, dialect)
        
        # 确定调度类型
        schedule_type = "CRON" if trigger_type == "CRON" else "ONCE"
        if task_def.loop_config and task_def.loop_config.get("max_rounds", 0) > 0:
            schedule_type = "LOOP"
        
        new_instance = await instance_repo.create(
            definition_id=def_id,
            trace_id=trace_id,
            input_params=input_params,
            schedule_type=schedule_type,
            round_index=0,
            depends_on=[]
        )
        
        # 4. 发送任务执行消息
        await self.broker.publish(
            topic="task.execute",
            message={
                "instance_id": new_instance.id,
                "trace_id": trace_id,
                "definition_id": def_id,
                "input_params": input_params,
                "schedule_type": schedule_type,
                "round_index": 0
            }
        )
        
        return trace_id
    
    async def handle_task_completed(
        self,
        session: AsyncSession,
        instance_id: str,
        status: str,
        output_ref: Optional[str] = None,
        error_msg: Optional[str] = None
    ):
        """处理任务完成事件"""
        # 1. 更新任务实例状态
        instance_repo = create_task_instance_repo(session, dialect)
        instance = await instance_repo.get(instance_id)
        
        if not instance:
            return
        
        # 2. 更新完成时间和状态
        await instance_repo.update_finished_at(
            instance_id=instance_id,
            finished_at=datetime.now(timezone.utc),
            status=status,
            output_ref=output_ref,
            error_msg=error_msg
        )
        
        # 3. 如果是循环任务且成功，检查是否需要执行下一轮
        if status == "SUCCESS" and instance.schedule_type == "LOOP":
            await self._handle_loop_next_round(session, instance)
    
    async def _handle_loop_next_round(self, session: AsyncSession, instance):
        """处理循环任务的下一轮"""
        # 1. 获取任务定义
        def_repo = create_task_definition_repo(session, dialect)
        task_def = await def_repo.get(instance.definition_id)
        
        if not task_def or not task_def.loop_config:
            return
        
        loop_config = task_def.loop_config
        max_rounds = loop_config.get("max_rounds", 0)
        interval_sec = loop_config.get("interval_sec", 60)
        
        # 2. 检查是否达到最大轮次
        if instance.round_index + 1 >= max_rounds:
            return
        
        # 3. 创建下一轮任务实例
        instance_repo = create_task_instance_repo(session, dialect)
        next_instance = await instance_repo.create(
            definition_id=instance.definition_id,
            trace_id=instance.trace_id,
            input_params=instance.input_params,
            schedule_type="LOOP",
            round_index=instance.round_index + 1,
            depends_on=[]
        )
        
        # 4. 发送延迟执行消息
        await self.broker.publish_delayed(
            topic="task.execute",
            message={
                "instance_id": next_instance.id,
                "trace_id": instance.trace_id,
                "definition_id": instance.definition_id,
                "input_params": instance.input_params,
                "schedule_type": "LOOP",
                "round_index": next_instance.round_index
            },
            delay_sec=interval_sec
        )
    
    async def handle_task_failed(
        self,
        session: AsyncSession,
        instance_id: str,
        error_msg: str
    ):
        """处理任务失败事件"""
        await self.handle_task_completed(
            session=session,
            instance_id=instance_id,
            status="FAILED",
            error_msg=error_msg
        )
    
    async def handle_task_started(
        self,
        session: AsyncSession,
        instance_id: str
    ):
        """处理任务开始执行事件"""
        instance_repo = create_task_instance_repo(session, dialect)
        await instance_repo.update_status(
            instance_id=instance_id,
            status="RUNNING"
        )
