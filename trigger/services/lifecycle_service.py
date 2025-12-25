import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Tuple

from sqlalchemy.ext.asyncio import AsyncSession

# 假定的导入路径，保持原样
from external.db.impl import create_task_definition_repo, create_task_instance_repo
from external.db.session import dialect
from external.messaging.base import MessageBroker
from events.event_publisher import event_publisher, control_external_task
from .scheduler_service import SchedulerService


class LifecycleService:
    """任务生命周期管理服务 (支持即席任务与管控)"""

    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.scheduler = SchedulerService(broker)

    # =========================================================================
    # 入口 1: 即席任务 (Ad-hoc) -> 先创建定义，再执行
    # =========================================================================
    async def submit_ad_hoc_task(
        self,
        session: AsyncSession,
        task_name: str,
        task_content: Dict[str, Any],
        input_params: Dict[str, Any],
        schedule_type: str = "IMMEDIATE",
        schedule_config: Optional[Dict[str, Any]] = None,
        loop_config: Optional[Dict[str, Any]] = None,
        is_temporary: bool = True,
        request_id: Optional[str] = None  # [新增] 参数
    ):
        # 1. 差异化逻辑：创建定义
        def_repo = create_task_definition_repo(session, dialect)
        new_def = await def_repo.create(
            name=task_name,
            content=task_content,
            loop_config=loop_config or {},
            is_temporary=is_temporary,
            created_at=datetime.now(timezone.utc)
        )
        
        # 2. 调用通用核心逻辑
        return await self._core_dispatch(
            session=session,
            def_id=new_def.id,
            input_params=input_params,
            schedule_type=schedule_type,
            schedule_config=schedule_config,
            loop_config=loop_config,
            request_id=request_id  # [新增] 透传
        )



    # =========================================================================
    # 核心统一逻辑 (Private)
    # =========================================================================
    async def _core_dispatch(
        self,
        session: AsyncSession,
        def_id: str,
        input_params: Dict[str, Any],
        schedule_type: str,
        schedule_config: Optional[Dict[str, Any]] = None,
        loop_config: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None # [新增] 参数
    ) -> str:
        """
        统一的调度 + 追踪入口
        """
        trace_id = str(uuid.uuid4())
        schedule_config = schedule_config or {}

        # [新增] 兜底逻辑：如果上游没传 request_id，这里再生成一个，防止日志中该字段为空
        final_request_id = request_id or str(uuid.uuid4())

        # 1. 统一调度 (消除了原来的 if/elif 重复)
        if schedule_type in ["ONCE", "IMMEDIATE"]:
            await self.scheduler.schedule_immediate(
                session=session, definition_id=def_id, input_params=input_params, trace_id=trace_id
            )
        elif schedule_type == "CRON":
            await self.scheduler.schedule_cron(
                session=session, definition_id=def_id,
                cron_expression=schedule_config.get("cron_expression"),
                input_params=input_params, trace_id=trace_id
            )
        elif schedule_type == "LOOP":
            # 安全获取循环配置
            max_rounds = loop_config.get("max_rounds", 1) if loop_config else 1
            interval_sec = loop_config.get("interval_sec") if loop_config else None
            await self.scheduler.schedule_loop(
                session=session, definition_id=def_id, input_params=input_params,
                max_rounds=max_rounds, loop_interval=interval_sec, trace_id=trace_id
            )
        elif schedule_type == "DELAYED":
            await self.scheduler.schedule_delayed(
                session=session, definition_id=def_id, input_params=input_params,
                delay_seconds=schedule_config.get("delay_seconds", 0), trace_id=trace_id
            )

        # 2. 统一发送 Trace 开始事件 (之前 Ad-hoc 任务可能漏了这个)
        await event_publisher.publish_start_trace(
            root_def_id=def_id,
            trace_id=trace_id,
            input_params=input_params,
            request_id=final_request_id  # [新增] 这里使用了 request_id
        )

        return trace_id

    # =========================================================================
    # 入口 2: 基于 ID 触发 (Pre-defined) -> 先查定义，再执行
    # =========================================================================
    async def start_new_trace(
        self,
        session: AsyncSession,
        def_id: str,
        input_params: dict,
        trigger_type: str = "CRON", # 兼容旧参数名，实际对应 schedule_type
        request_id: Optional[str] = None  # [新增] 参数
    ):
        # 1. 差异化逻辑：检查定义是否存在，并获取配置
        def_repo = create_task_definition_repo(session, dialect)
        task_def = await def_repo.get(def_id)
        if not task_def:
            raise ValueError(f"Task Definition {def_id} not found")

        # 2. 准备配置 (兼容逻辑：如果是 CRON，从数据库读表达式)
        schedule_config = {}
        target_schedule_type = trigger_type
        
        if trigger_type == "CRON":
            if task_def.cron_expr:
                schedule_config["cron_expression"] = task_def.cron_expr
            else:
                # 如果触发类型是 CRON 但库里没配，降级为立即执行或报错，这里假设降级
                target_schedule_type = "IMMEDIATE"

        # 3. 调用通用核心逻辑
        return await self._core_dispatch(
            session=session,
            def_id=def_id,
            input_params=input_params,
            schedule_type=target_schedule_type,
            schedule_config=schedule_config,
            loop_config=task_def.loop_config, # 复用库里的循环配置
            request_id=request_id  # [新增] 透传
        )

    # =========================================================================
    # 任务状态回调处理
    # =========================================================================
    async def handle_task_completed(
        self, session: AsyncSession, instance_id: str, status: str, 
        output_ref: Optional[str] = None, error_msg: Optional[str] = None
    ):
        instance_repo = create_task_instance_repo(session, dialect)
        instance = await instance_repo.get(instance_id)
        if not instance: return
        
        await instance_repo.update_finished_at(
            instance_id=instance_id, finished_at=datetime.now(timezone.utc),
            status=status, output_ref=output_ref, error_msg=error_msg
        )
        
        if status == "SUCCESS" and instance.schedule_type == "LOOP":
            await self._handle_loop_next_round(session, instance)

    async def _handle_loop_next_round(self, session: AsyncSession, instance):
        def_repo = create_task_definition_repo(session, dialect)
        task_def = await def_repo.get(instance.definition_id)
        
        if not task_def or not task_def.loop_config: return
        
        loop_config = task_def.loop_config
        max_rounds = loop_config.get("max_rounds", 0)
        
        if instance.round_index + 1 >= max_rounds: return
        
        # 复用逻辑：创建新实例并发送延迟消息
        # 这里逻辑较重且特定，保持现状，或者可以移动到 SchedulerService 中
        instance_repo = create_task_instance_repo(session, dialect)
        next_instance = await instance_repo.create(
            definition_id=instance.definition_id,
            trace_id=instance.trace_id,
            input_params=instance.input_params,
            schedule_type="LOOP",
            round_index=instance.round_index + 1,
            depends_on=[]
        )
        
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
            delay_sec=loop_config.get("interval_sec", 60)
        )

    async def handle_task_failed(self, session: AsyncSession, instance_id: str, error_msg: str):
        await self.handle_task_completed(session, instance_id, "FAILED", error_msg=error_msg)

    async def handle_task_started(self, session: AsyncSession, instance_id: str):
        instance_repo = create_task_instance_repo(session, dialect)
        await instance_repo.update_status(instance_id=instance_id, status="RUNNING")

    # =========================================================================
    # 任务控制功能 (Cancel, Pause, Resume, Modify)
    # =========================================================================
    
    async def cancel_task(self, session: AsyncSession, instance_id: Optional[str] = None, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """批量或单条取消任务"""
        instance_repo = create_task_instance_repo(session, dialect)
        instances = []
        if instance_id:
            inst = await instance_repo.get(instance_id)
            if inst: instances.append(inst)
        elif trace_id:
            instances = await instance_repo.list_by_trace_id(trace_id)
        
        if not instances:
            return {"success": False, "message": "No tasks found", "affected_instances": []}
        
        results = {"affected": [], "failed": []}
        
        for instance in instances:
            try:
                # 核心逻辑提取：判断是该调外部接口，还是直接改库
                success, _ = await self._perform_control_action(
                    repo=instance_repo,
                    instance=instance,
                    action_type="CANCEL",
                    target_status="CANCELLED",
                    external_error_msg="Task cancelled by user",
                    internal_error_msg="Task cancelled internally"
                )
                if success:
                    results["affected"].append(instance.id)
                else:
                    results["failed"].append(instance.id)
            except Exception:
                results["failed"].append(instance.id)
                
        success_all = len(results["failed"]) == 0
        return {
            "success": success_all,
            "message": f"Processed {len(instances)} tasks. Success: {len(results['affected'])}, Failed: {len(results['failed'])}",
            "affected_instances": results["affected"],
            "failed_instances": results["failed"]
        }

    async def pause_task(self, session: AsyncSession, instance_id: Optional[str] = None, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Pause task by instance_id or trace_id"""
        instance_repo = create_task_instance_repo(session, dialect)
        instances = []
        if instance_id:
            inst = await instance_repo.get(instance_id)
            if inst: instances.append(inst)
        elif trace_id:
            instances = await instance_repo.list_by_trace_id(trace_id)
        
        if not instances:
            return {"success": False, "message": "No tasks found", "affected_instances": []}
        
        results = {"affected": [], "failed": []}
        
        for instance in instances:
            try:
                success, details = await self._perform_control_action(
                    repo=instance_repo,
                    instance=instance,
                    action_type="PAUSE",
                    target_status="PAUSED"
                )
                if success:
                    results["affected"].append(instance.id)
                else:
                    results["failed"].append(instance.id)
            except Exception:
                results["failed"].append(instance.id)
                
        success_all = len(results["failed"]) == 0
        return {
            "success": success_all,
            "message": f"Processed {len(instances)} tasks. Success: {len(results['affected'])}, Failed: {len(results['failed'])}",
            "affected_instances": results["affected"],
            "failed_instances": results["failed"]
        }

    async def resume_task(self, session: AsyncSession, instance_id: Optional[str] = None, trace_id: Optional[str] = None) -> Dict[str, Any]:
        """Resume task by instance_id or trace_id"""
        instance_repo = create_task_instance_repo(session, dialect)
        instances = []
        if instance_id:
            inst = await instance_repo.get(instance_id)
            if inst: instances.append(inst)
        elif trace_id:
            instances = await instance_repo.list_by_trace_id(trace_id)
        
        if not instances:
            return {"success": False, "message": "No tasks found", "affected_instances": []}
        
        results = {"affected": [], "failed": []}
        
        for instance in instances:
            try:
                if instance.status != "PAUSED":
                    results["failed"].append(instance.id)
                    continue
                
                # 区分逻辑：如果是外部推送过的暂停，需要外部恢复；否则内部恢复为 PENDING
                is_external = getattr(instance, "external_status_pushed", False)
                target_status = "RUNNING" if is_external else "PENDING"
                
                success, details = await self._perform_control_action(
                    repo=instance_repo,
                    instance=instance,
                    action_type="RESUME",
                    target_status=target_status
                )
                if success:
                    results["affected"].append(instance.id)
                else:
                    results["failed"].append(instance.id)
            except Exception:
                results["failed"].append(instance.id)
                
        success_all = len(results["failed"]) == 0
        return {
            "success": success_all,
            "message": f"Processed {len(instances)} tasks. Success: {len(results['affected'])}, Failed: {len(results['failed'])}",
            "affected_instances": results["affected"],
            "failed_instances": results["failed"]
        }

    async def modify_task(
        self, session: AsyncSession, instance_id: Optional[str] = None, trace_id: Optional[str] = None,
        input_params: Optional[Dict] = None, schedule_config: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Modify task by instance_id or trace_id"""
        instance_repo = create_task_instance_repo(session, dialect)
        instances = []
        if instance_id:
            inst = await instance_repo.get(instance_id)
            if inst: instances.append(inst)
        elif trace_id:
            instances = await instance_repo.list_by_trace_id(trace_id)
        
        if not instances:
            return {"success": False, "message": "No tasks found", "affected_instances": []}
        
        results = {"affected": [], "failed": []}
        updates = {}
        if input_params: updates["input_params"] = input_params
        if schedule_config: updates["schedule_config"] = schedule_config
        
        if not updates:
            return {"success": False, "message": "No fields to modify"}
        
        for instance in instances:
            try:
                if instance.status in ["RUNNING", "DISPATCHED"]:
                    results["failed"].append(instance.id)
                    continue
                
                if hasattr(instance_repo, "update_instance"):
                    await instance_repo.update_instance(instance_id=instance.id, **updates)
                else:
                    # Fallback updates
                    if input_params: await instance_repo.update_input_params(instance.id, input_params)
                    if schedule_config: await instance_repo.update_schedule_config(instance.id, schedule_config)
                
                results["affected"].append(instance.id)
            except Exception as e:
                results["failed"].append(instance.id)
                
        success_all = len(results["failed"]) == 0
        return {
            "success": success_all,
            "message": f"Processed {len(instances)} tasks. Success: {len(results['affected'])}, Failed: {len(results['failed'])}",
            "affected_instances": results["affected"],
            "failed_instances": results["failed"],
            "details": {"modified_fields": list(updates.keys())}
        }

    # =========================================================================
    # 内部辅助方法 (Reduce Duplication)
    # =========================================================================
    
    async def _single_instance_control(
        self, session: AsyncSession, instance_id: str, 
        action_type: str, target_status: str, instance_obj=None
    ) -> Dict[str, Any]:
        """处理单实例控制操作的模板方法"""
        repo = create_task_instance_repo(session, dialect)
        instance = instance_obj or await repo.get(instance_id)
        
        if not instance:
            return {"success": False, "message": f"Task {instance_id} not found"}
            
        try:
            success, details = await self._perform_control_action(
                repo=repo, instance=instance, action_type=action_type, target_status=target_status
            )
            return {
                "success": success,
                "message": f"Action {action_type} {'succeeded' if success else 'failed'}",
                "details": details
            }
        except Exception as e:
            return {"success": False, "message": str(e), "details": {"error": str(e)}}

    async def _perform_control_action(
        self, repo, instance, action_type: str, target_status: str,
        external_error_msg: str = None, internal_error_msg: str = None
    ) -> Tuple[bool, Dict]:
        """
        核心控制逻辑：
        判断任务是否已经分发(DISPATCHED/RUNNING/PAUSED_EXTERNAL)，
        如果是 -> 调用 external_task 接口
        否则 -> 直接更新数据库状态
        """
        original_status = instance.status
        # 判断是否涉及外部系统交互
        # 注意：RESUME 时，如果当前是 PAUSED 且有过 external_push，也被视为需要外部交互
        is_external_active = instance.status in ["RUNNING", "DISPATCHED"]
        if action_type == "RESUME" and getattr(instance, "external_status_pushed", False):
            is_external_active = True

        if is_external_active:
            # === 分支 A: 调用外部系统 ===
            external_success = await control_external_task(
                task_id=instance.id,
                action=action_type
            )
            
            details = {"original_status": original_status, "control_type": "external"}
            
            if external_success:
                update_kwargs = {"instance_id": instance.id, "status": target_status}
                if external_error_msg: update_kwargs["error_msg"] = external_error_msg
                await repo.update_status(**update_kwargs)
                details["new_status"] = target_status
                return True, details
            else:
                return False, details
        else:
            # === 分支 B: 纯内部状态更新 ===
            update_kwargs = {"instance_id": instance.id, "status": target_status}
            if internal_error_msg: update_kwargs["error_msg"] = internal_error_msg
            await repo.update_status(**update_kwargs)
            
            return True, {
                "original_status": original_status, 
                "new_status": target_status, 
                "control_type": "internal"
            }