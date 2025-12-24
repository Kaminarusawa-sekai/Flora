import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any

from external.db.impl import create_task_definition_repo, create_task_instance_repo
from external.db.session import dialect
from external.messaging.base import MessageBroker
from events.event_publisher import event_publisher
from common.enums import ScheduleType
from .scheduler_service import SchedulerService


class LifecycleService:
    """任务生命周期管理服务 (支持即席任务)"""
    
    def __init__(self, broker: MessageBroker):
        self.broker = broker
        self.scheduler = SchedulerService(broker)

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
        is_temporary: bool = True, # 标记是否为临时定义，方便后续清理
        # 新增参数，用于指定调度类型
        schedule_type: str = "IMMEDIATE",  # 保持兼容，可以是 "IMMEDIATE", "CRON", "LOOP", "DELAYED"
        schedule_config: Optional[Dict[str, Any]] = None
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
            loop_config=loop_config or {},    # 循环配置：如果有，存入数据库
            is_temporary=is_temporary,  # 标记位：这是一个临时生成的定义
            created_at=datetime.now(timezone.utc)
        )
        
        # 拿到生成的 ID
        def_id = new_def.id
        
        # --- 步骤 2: 根据调度类型创建调度任务 ---
        trace_id = str(uuid.uuid4())
        
        if schedule_type in ["ONCE", "IMMEDIATE"] or not schedule_config:
            # 即时任务
            await self.scheduler.schedule_immediate(
                session=session,
                definition_id=def_id,
                input_params=input_params,
                trace_id=trace_id
            )
        elif schedule_type == "CRON":
            cron_expr = schedule_config.get("cron_expression")
            if cron_expr:
                await self.scheduler.schedule_cron(
                    session=session,
                    definition_id=def_id,
                    cron_expression=cron_expr,
                    input_params=input_params,
                    trace_id=trace_id
                )
        elif schedule_type == "LOOP":
            max_rounds = loop_config.get("max_rounds", 1) if loop_config else 1
            interval_sec = loop_config.get("interval_sec") if loop_config else None
            
            await self.scheduler.schedule_loop(
                session=session,
                definition_id=def_id,
                input_params=input_params,
                max_rounds=max_rounds,
                loop_interval=interval_sec,
                trace_id=trace_id
            )
        elif schedule_type == "DELAYED":
            delay_seconds = schedule_config.get("delay_seconds", 0)
            await self.scheduler.schedule_delayed(
                session=session,
                definition_id=def_id,
                input_params=input_params,
                delay_seconds=delay_seconds,
                trace_id=trace_id
            )
        
        return trace_id

    # =========================================================================
    # 兼容旧场景：基于已有 ID 触发 (Pre-defined)
    # =========================================================================
    async def trigger_by_id(self, session: AsyncSession, def_id: str, input_params: dict):
        """基于已有的定义ID触发 (适用于定时任务调度器或引用公共库任务)"""
        # 使用新的调度服务直接触发即时任务
        return await self.scheduler.schedule_immediate(
            session=session,
            definition_id=def_id,
            input_params=input_params
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
        
        # 2. 根据触发类型使用新的调度服务
        if trigger_type == "CRON" and task_def.cron_expr:
            # 需要先获取任务定义的CRON表达式
            await self.scheduler.schedule_cron(
                session=session,
                definition_id=def_id,
                cron_expression=task_def.cron_expr,
                input_params=input_params,
                trace_id=trace_id
            )
        else:
            # 其他类型当作即时任务处理
            await self.scheduler.schedule_immediate(
                session=session,
                definition_id=def_id,
                input_params=input_params,
                trace_id=trace_id
            )
        
        # 3. 发事件
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
    
    # =========================================================================
    # 任务控制功能
    # =========================================================================
    async def cancel_task(
        self,
        session: AsyncSession,
        instance_id: Optional[str] = None,
        trace_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """取消任务
        
        Args:
            session: 数据库会话
            instance_id: 任务实例ID（可选）
            trace_id: 跟踪ID（可选）- 如果提供，取消该trace下的所有任务
        
        Returns:
            Dict[str, Any]: 取消操作结果，包含success、message和affected_instances
        """
        from ..events.event_publisher import control_external_task
        
        # 1. 获取需要取消的任务实例
        instance_repo = create_task_instance_repo(session, dialect)
        instances = []
        
        if instance_id:
            instance = await instance_repo.get(instance_id)
            if instance:
                instances = [instance]
        elif trace_id:
            instances = await instance_repo.list_by_trace_id(trace_id)
        
        if not instances:
            return {
                "success": False,
                "message": "No tasks found to cancel",
                "affected_instances": []
            }
        
        # 2. 逐个取消任务
        success_count = 0
        failed_instances = []
        affected_instances = []
        
        for instance in instances:
            try:
                affected_instances.append(instance.id)
                
                # 3. 检查任务状态，判断是内部取消还是外部取消
                if instance.status in ["RUNNING", "DISPATCHED"]:
                    # 已发出去的任务，调用外部系统取消
                    external_success = await control_external_task(
                        task_id=instance.id,
                        action="CANCEL"
                    )
                    # 更新内部状态
                    await instance_repo.update_status(
                        instance_id=instance.id,
                        status="CANCELLED",
                        error_msg="Task cancelled by user"
                    )
                    
                    if external_success:
                        success_count += 1
                    else:
                        failed_instances.append(instance.id)
                else:
                    # 未发出去的任务，直接内部取消
                    await instance_repo.update_status(
                        instance_id=instance.id,
                        status="CANCELLED",
                        error_msg="Task cancelled internally"
                    )
                    success_count += 1
            except Exception as e:
                failed_instances.append(instance.id)
        
        if success_count == len(instances):
            return {
                "success": True,
                "message": f"Successfully cancelled {success_count} task(s)",
                "affected_instances": affected_instances,
                "failed_instances": []
            }
        else:
            return {
                "success": False,
                "message": f"Cancelled {success_count} task(s), failed to cancel {len(failed_instances)} task(s)",
                "affected_instances": affected_instances,
                "failed_instances": failed_instances
            }
    
    async def pause_task(
        self,
        session: AsyncSession,
        instance_id: str
    ) -> Dict[str, Any]:
        """暂停任务
        
        Args:
            session: 数据库会话
            instance_id: 任务实例ID
        
        Returns:
            Dict[str, Any]: 暂停操作结果，包含success、message和details
        """
        from ..events.event_publisher import control_external_task
        
        # 1. 获取任务实例
        instance_repo = create_task_instance_repo(session, dialect)
        instance = await instance_repo.get(instance_id)
        
        if not instance:
            return {
                "success": False,
                "message": f"Task instance {instance_id} not found",
                "details": {
                    "instance_id": instance_id,
                    "current_status": None
                }
            }
        
        try:
            original_status = instance.status
            
            # 2. 检查任务状态，判断是内部暂停还是外部暂停
            if instance.status in ["RUNNING", "DISPATCHED"]:
                # 已发出去的任务，调用外部系统暂停
                external_success = await control_external_task(
                    task_id=instance.id,
                    action="PAUSE"
                )
                
                if external_success:
                    # 更新内部状态
                    await instance_repo.update_status(
                        instance_id=instance.id,
                        status="PAUSED"
                    )
                    return {
                        "success": True,
                        "message": f"Successfully paused task {instance_id}",
                        "details": {
                            "instance_id": instance_id,
                            "original_status": original_status,
                            "new_status": "PAUSED",
                            "control_type": "external"
                        }
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Failed to pause task {instance_id} via external system",
                        "details": {
                            "instance_id": instance_id,
                            "current_status": original_status,
                            "control_type": "external"
                        }
                    }
            else:
                # 未发出去的任务，直接内部暂停
                await instance_repo.update_status(
                    instance_id=instance.id,
                    status="PAUSED"
                )
                return {
                    "success": True,
                    "message": f"Successfully paused task {instance_id} internally",
                    "details": {
                        "instance_id": instance_id,
                        "original_status": original_status,
                        "new_status": "PAUSED",
                        "control_type": "internal"
                    }
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error pausing task {instance_id}: {str(e)}",
                "details": {
                    "instance_id": instance_id,
                    "error": str(e)
                }
            }
    
    async def resume_task(
        self,
        session: AsyncSession,
        instance_id: str
    ) -> Dict[str, Any]:
        """继续任务
        
        Args:
            session: 数据库会话
            instance_id: 任务实例ID
        
        Returns:
            Dict[str, Any]: 继续操作结果，包含success、message和details
        """
        from ..events.event_publisher import control_external_task
        
        # 1. 获取任务实例
        instance_repo = create_task_instance_repo(session, dialect)
        instance = await instance_repo.get(instance_id)
        
        if not instance:
            return {
                "success": False,
                "message": f"Task instance {instance_id} not found",
                "details": {
                    "instance_id": instance_id,
                    "current_status": None
                }
            }
        
        try:
            original_status = instance.status
            
            # 2. 检查任务状态，判断是内部继续还是外部继续
            if instance.status == "PAUSED":
                # 已暂停的任务，判断是外部暂停还是内部暂停
                if hasattr(instance, "external_status_pushed") and instance.external_status_pushed:
                    # 调用外部系统继续
                    external_success = await control_external_task(
                        task_id=instance.id,
                        action="RESUME"
                    )
                    
                    if external_success:
                        # 更新内部状态
                        await instance_repo.update_status(
                            instance_id=instance.id,
                            status="RUNNING"
                        )
                        return {
                            "success": True,
                            "message": f"Successfully resumed task {instance_id}",
                            "details": {
                                "instance_id": instance_id,
                                "original_status": original_status,
                                "new_status": "RUNNING",
                                "control_type": "external"
                            }
                        }
                    else:
                        return {
                            "success": False,
                            "message": f"Failed to resume task {instance_id} via external system",
                            "details": {
                                "instance_id": instance_id,
                                "current_status": original_status,
                                "control_type": "external"
                            }
                        }
                else:
                    # 内部暂停的任务，直接更新状态
                    new_status = "PENDING"
                    await instance_repo.update_status(
                        instance_id=instance.id,
                        status=new_status
                    )
                    return {
                        "success": True,
                        "message": f"Successfully resumed task {instance_id} internally",
                        "details": {
                            "instance_id": instance_id,
                            "original_status": original_status,
                            "new_status": new_status,
                            "control_type": "internal"
                        }
                    }
            else:
                return {
                    "success": False,
                    "message": f"Cannot resume task {instance_id}: current status is {original_status}",
                    "details": {
                        "instance_id": instance_id,
                        "current_status": original_status
                    }
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error resuming task {instance_id}: {str(e)}",
                "details": {
                    "instance_id": instance_id,
                    "error": str(e)
                }
            }
    
    async def modify_task(
        self,
        session: AsyncSession,
        instance_id: str,
        input_params: Optional[Dict[str, Any]] = None,
        schedule_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """修改任务
        
        Args:
            session: 数据库会话
            instance_id: 任务实例ID
            input_params: 新的输入参数（可选）
            schedule_config: 新的调度配置（可选）
        
        Returns:
            Dict[str, Any]: 修改操作结果，包含success、message和details
        """
        from ..events.event_publisher import control_external_task
        
        # 1. 获取任务实例
        instance_repo = create_task_instance_repo(session, dialect)
        instance = await instance_repo.get(instance_id)
        
        if not instance:
            return {
                "success": False,
                "message": f"Task instance {instance_id} not found",
                "details": {
                    "instance_id": instance_id,
                    "current_status": None
                }
            }
        
        try:
            original_status = instance.status
            
            # 2. 检查任务状态
            if instance.status in ["RUNNING", "DISPATCHED"]:
                # 已发出去的任务，没法修改，直接返回失败
                modified_fields = []
                if input_params:
                    modified_fields.append("input_params")
                if schedule_config:
                    modified_fields.append("schedule_config")
                    
                return {
                    "success": False,
                    "message": f"Cannot modify task {instance_id}: task is already running or dispatched",
                    "details": {
                        "instance_id": instance_id,
                        "current_status": original_status,
                        "modified_fields": modified_fields
                    }
                }
            else:
                # 未发出去的任务，直接更新内部数据
                update_data = {}
                modified_fields = []
                
                if input_params:
                    update_data["input_params"] = input_params
                    modified_fields.append("input_params")
                if schedule_config:
                    update_data["schedule_config"] = schedule_config
                    modified_fields.append("schedule_config")
                
                if not modified_fields:
                    return {
                        "success": False,
                        "message": f"No fields provided to modify for task {instance_id}",
                        "details": {
                            "instance_id": instance_id,
                            "current_status": original_status
                        }
                    }
                
                # 调用存储库更新方法（假设存在）
                if hasattr(instance_repo, "update_instance"):
                    await instance_repo.update_instance(
                        instance_id=instance_id,
                        **update_data
                    )
                else:
                    # 如果没有直接的update_instance方法，可能需要更新特定字段
                    if input_params:
                        await instance_repo.update_input_params(
                            instance_id=instance_id,
                            input_params=input_params
                        )
                    if schedule_config:
                        await instance_repo.update_schedule_config(
                            instance_id=instance_id,
                            schedule_config=schedule_config
                        )
                
                return {
                    "success": True,
                    "message": f"Successfully modified task {instance_id} internally",
                    "details": {
                        "instance_id": instance_id,
                        "current_status": original_status,
                        "control_type": "internal",
                        "modified_fields": modified_fields
                    }
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Error modifying task {instance_id}: {str(e)}",
                "details": {
                    "instance_id": instance_id,
                    "error": str(e)
                }
            }
