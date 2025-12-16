from datetime import datetime
from typing import Dict, Any, Optional
from ...external.db.base import TaskInstanceRepository, TaskDefinitionRepository
from ...external.messaging.base import MessageBroker
from ...common.enums import TaskInstanceStatus, ScheduleType
from ...common.task_instance import TaskInstance


class LoopController:
    """
    循环控制器，负责管理 LOOP 类型任务的多轮执行
    """

    def __init__(
        self,
        inst_repo: TaskInstanceRepository,
        def_repo: TaskDefinitionRepository,
        broker: MessageBroker
    ):
        self.inst_repo = inst_repo
        self.def_repo = def_repo
        self.broker = broker

    async def handle_loop_round_completed(self, task_id: str, output_ref: str):
        """
        处理循环轮次完成事件
        """
        task = await self.inst_repo.get(task_id)
        
        # 确保任务是 LOOP 类型
        if task.schedule_type != ScheduleType.LOOP:
            return
        
        # 获取任务定义
        definition = await self.def_repo.get(task.definition_id)
        
        # 检查是否需要继续循环
        max_rounds = definition.loop_config.get("max_rounds", 1)
        current_round = task.round_index or 0
        
        if current_round + 1 < max_rounds:
            # 计算下一轮的输入参数（可以基于上一轮的输出）
            next_input_params = await self._calculate_next_input_params(task, output_ref)
            
            # 创建下一轮任务实例
            next_round_task = await self._create_next_round_task(task, definition, next_input_params, current_round + 1)
            
            # 获取循环间隔
            interval = definition.loop_config.get("interval_sec", 10)
            
            # 延时调度下一轮任务
            await self.broker.publish_delayed(
                "task.execute",
                {"instance_id": next_round_task.id},
                delay_sec=interval
            )

    async def _calculate_next_input_params(self, task: TaskInstance, output_ref: str) -> Dict[str, Any]:
        """
        计算下一轮任务的输入参数
        可以基于上一轮的输出进行计算
        """
        # 默认使用当前任务的输入参数
        next_params = task.input_params.copy()
        
        # 可以在这里添加更复杂的逻辑，比如基于 output_ref 读取结果并更新参数
        # 例如：next_params["previous_result"] = await self._read_result_from_ref(output_ref)
        
        return next_params

    async def _create_next_round_task(
        self,
        current_task: TaskInstance,
        definition: Any,
        next_input_params: Dict[str, Any],
        next_round_index: int
    ) -> TaskInstance:
        """
        创建下一轮任务实例
        """
        # 使用与当前任务相同的配置，除了 round_index 和输入参数
        next_task = TaskInstance(
            id=f"{current_task.id}-round-{next_round_index}",
            trace_id=current_task.trace_id,
            parent_id=current_task.parent_id,
            job_id=current_task.job_id,
            actor_type=current_task.actor_type,
            role=current_task.role,
            layer=current_task.layer,
            is_leaf_agent=current_task.is_leaf_agent,
            schedule_type=ScheduleType.LOOP,
            round_index=next_round_index,
            cron_trigger_time=None,
            status=TaskInstanceStatus.PENDING,
            node_path=current_task.node_path,
            depth=current_task.depth,
            depends_on=current_task.depends_on,
            split_count=current_task.split_count,
            completed_children=current_task.completed_children,
            input_params=next_input_params,
            output_ref=None,
            error_msg=None,
            started_at=None,
            finished_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        await self.inst_repo.create(next_task)
        return next_task