import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from ..external.db.impl import create_task_definition_repo, create_task_instance_repo
from ..external.db.session import dialect
from ..external.messaging.base import MessageBroker
from ..events.event_publisher import event_publisher


class LifecycleService:
    """任务生命周期管理服务 (支持即席任务)"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker

    # =========================================================================
    # 核心场景：即席任务 (Ad-hoc)
    # 场景：请求里既有代码/配置，也有参数。
    # =========================================================================
    async def submit_ad_hoc_task(
        self,
        session: AsyncSession,
        task_name: str,
        task_content: Dict[str, Any],  # 具体的执行逻辑，如 {"script": "print('hello')", "image": "python:3.9"}
        input_params: Dict[str, Any],
        loop_config: Optional[Dict[str, Any]] = None, # 如果这个临时任务需要循环，就在这里传
        is_temporary: bool = True # 标记是否为临时定义，方便后续清理
    ):
        """
        处理【定义+实例】一起过来的请求。
        1. 先创建(或更新) TaskDefinition
        2. 再启动 TaskInstance
        """
        
        # --- 步骤 1: 处理定义 (Definition) ---
        def_repo = create_task_definition_repo(session, dialect)
        
        # 创建一个新的定义记录
        # 注意：这里假设 Repo 有 create 方法，且返回创建的对象
        # 在实际业务中，也可以根据 task_name 生成 hash 来判断是否复用已有的 Definition
        new_def = await def_repo.create(
            name=task_name,
            content=task_content,       # 核心逻辑：代码、镜像地址等
            loop_config=loop_config,    # 循环配置：如果有，存入数据库
            is_temporary=is_temporary,  # 标记位：这是一个临时生成的定义
            created_at=datetime.now(timezone.utc)
        )
        
        # 拿到生成的 ID
        def_id = new_def.id
        
        # --- 步骤 2: 启动实例 (Instance) ---
        # 既然定义里已经存了 loop_config，我们直接用通用逻辑启动即可
        # 如果 loop_config 有值，_start_trace_core 会自动识别为 LOOP 模式
        # 如果 loop_config 为空，则自动识别为 ONCE 模式
        
        return await self._start_trace_core(
            session=session,
            def_id=def_id,
            input_params=input_params,
            trigger_type="API", # 标记为 API 触发
            force_run_once=False
        )

    # =========================================================================
    # 兼容旧场景：基于已有 ID 触发 (Pre-defined)
    # =========================================================================
    async def trigger_by_id(self, session: AsyncSession, def_id: str, input_params: dict):
        """基于已有的定义ID触发 (适用于定时任务调度器或引用公共库任务)"""
        return await self._start_trace_core(
            session=session, def_id=def_id, input_params=input_params,
            trigger_type="API"
        )

    # =========================================================================
    # 内部核心逻辑 (保持复用)
    # =========================================================================
    async def _start_trace_core(
        self,
        session: AsyncSession,
        def_id: str,
        input_params: dict,
        trigger_type: str,
        force_run_once: bool = False
    ):
        # 1. 获取定义 (刚创建的，或者已有的)
        def_repo = create_task_definition_repo(session, dialect)
        task_def = await def_repo.get(def_id)
        if not task_def: return None
        
        trace_id = str(uuid.uuid4())
        
        # 2. 判定调度逻辑
        if force_run_once:
            schedule_type = "ONCE"
        else:
            # 这里的逻辑完美兼容了 Ad-hoc 任务：
            # 如果你在 submit_ad_hoc_task 里传了 loop_config，这里就会读出来变成 LOOP
            # 如果没传，这里就是 ONCE
            base_type = "CRON" if trigger_type == "CRON" else "ONCE"
            if task_def.loop_config and task_def.loop_config.get("max_rounds", 0) > 0:
                schedule_type = "LOOP"
            else:
                schedule_type = base_type

        # 3. 创建实例
        instance_repo = create_task_instance_repo(session, dialect)
        new_instance = await instance_repo.create(
            definition_id=def_id,
            trace_id=trace_id,
            input_params=input_params,
            schedule_type=schedule_type,
            round_index=0,
            depends_on=[]
        )
        
        # 4. 发消息 (Worker 收到消息后，会根据 definition_id 去库里查刚才存的 content)
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
        
        # 5. 发事件
        await event_publisher.publish_start_trace(
            root_def_id=def_id,
            trace_id=trace_id,
            input_params=input_params
        )
        
        return trace_id

    # 保持对原有方法的兼容，避免破坏现有调用
    async def start_new_trace(
        self,
        session: AsyncSession,
        def_id: str,
        input_params: dict,
        trigger_type: str = "CRON"
    ):
        """启动一个新的任务Trace（兼容旧接口）"""
        return await self._start_trace_core(
            session=session,
            def_id=def_id,
            input_params=input_params,
            trigger_type=trigger_type,
            force_run_once=False
        )
    
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
