from events.command_tower.models import TaskEvent
from events.common.actor_dto import ActorType


class EventProcessor:
    """
    事件处理器/任务跟踪器
    消费MQ中的TaskEvent，驱动状态机，触发聚合
    """
    
    def __init__(self, db_client):
        """
        初始化事件处理器
        
        Args:
            db_client: 数据库客户端，需支持相关查询和更新方法
        """
        self.db = db_client
    
    def process_event(self, event: TaskEvent) -> bool:
        """
        处理任务事件
        
        Args:
            event: 任务事件
            
        Returns:
            处理结果，True表示成功
        """
        # 1. 去重检查
        if self.db.is_event_processed(event.event_id):
            return True  # 事件已处理，直接返回成功
        
        # 2. 更新task_instances状态、时间戳、错误信息
        self.db.update_task_status(
            task_id=event.task_id,
            status=event.status,
            error_info=event.error_info,
            result=event.result,
            updated_at=event.timestamp
        )
        
        # 3. 处理完成事件，更新completed_children并检查聚合条件
        if event.status in ["COMPLETED", "FAILED", "CANCELLED"]:
            self._handle_completion_event(event)
        
        # 4. 标记事件为已处理
        self.db.mark_event_processed(event.event_id)
        
        return True
    
    def _handle_completion_event(self, event: TaskEvent):
        """
        处理完成事件
        
        Args:
            event: 完成类型的任务事件
        """
        # 更新父任务的completed_children计数
        if event.parent_id:
            self.db.increment_completed_children(event.parent_id)
            
            # 获取父任务
            parent = self.db.get_task(event.parent_id)
            if not parent:
                return
            
            # 检查是否需要触发聚合
            if parent.actor_type == ActorType.SINGLE_AGGREGATOR:
                # SingleAgg 完成 → 检查并通知其父 GroupAgg
                self._check_group_agg_ready(parent.parent_id)
            
            elif parent.actor_type == ActorType.GROUP_AGGREGATOR:
                # GroupAgg 的所有 SingleAgg 完成？
                if parent.completed_children == parent.split_count:
                    # 标记GroupAgg为已完成
                    self.db.mark_group_agg_as_completed(parent.id)
                    # 递归向上通知更上层Agent
                    self._check_group_agg_ready(parent.parent_id)
    
    def _check_group_agg_ready(self, group_agg_id: str):
        """
        检查GroupAggregator是否已准备好聚合
        
        Args:
            group_agg_id: GroupAggregator的任务ID
        """
        if not group_agg_id:
            return
        
        group_agg = self.db.get_task(group_agg_id)
        if not group_agg:
            return
        
        # 检查GroupAgg的所有子任务是否都已完成
        if group_agg.actor_type == ActorType.GROUP_AGGREGATOR:
            if group_agg.completed_children == group_agg.split_count:
                self.db.mark_group_agg_as_completed(group_agg.id)
                # 递归向上检查
                self._check_group_agg_ready(group_agg.parent_id)
