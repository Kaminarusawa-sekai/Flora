from events.command_tower.models import ControlEvent


class SignalController:
    """
    信号控制器
    管理控制指令的下发与持久化，实现"遥控器"能力
    """
    
    def __init__(self, redis_client, db_client):
        """
        初始化信号控制器
        
        Args:
            redis_client: Redis客户端，用于实时信号存储
            db_client: 数据库客户端，用于持久化控制事件
        """
        self.redis = redis_client
        self.db = db_client
    
    def process_control_event(self, event: ControlEvent) -> bool:
        """
        处理控制事件
        
        Args:
            event: 控制事件
            
        Returns:
            处理结果，True表示成功
        """
        # 写入Redis，供执行器实时查询
        if event.task_id:
            # 任务级控制
            redis_key = f"cmd:task:{event.task_id}"
        else:
            # 全局控制
            redis_key = f"cmd:instance:{event.trace_id}"
        
        # 写入Redis哈希
        self.redis.hset(redis_key, "global_action", event.event_type.value)
        
        # 同时写入control_events表（用于审计/恢复）
        self.db.insert_control_event(event)
        
        return True
    
    def get_current_signal(self, trace_id: str, task_id: str = None) -> str:
        """
        获取当前信号
        
        Args:
            trace_id: 跟踪ID
            task_id: 可选，任务ID，用于获取任务级信号
            
        Returns:
            当前信号值，如"CANCEL"，若没有则返回None
        """
        # 优先查询任务级信号
        if task_id:
            redis_key = f"cmd:task:{task_id}"
            signal = self.redis.hget(redis_key, "global_action")
            if signal:
                return signal
        
        # 查询全局信号
        redis_key = f"cmd:instance:{trace_id}"
        return self.redis.hget(redis_key, "global_action")
    
    def clear_signal(self, trace_id: str, task_id: str = None) -> bool:
        """
        清除信号
        
        Args:
            trace_id: 跟踪ID
            task_id: 可选，任务ID
            
        Returns:
            清除结果，True表示成功
        """
        if task_id:
            redis_key = f"cmd:task:{task_id}"
            self.redis.delete(redis_key)
        else:
            redis_key = f"cmd:instance:{trace_id}"
            self.redis.delete(redis_key)
        
        return True
