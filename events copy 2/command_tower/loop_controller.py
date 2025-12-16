from datetime import datetime
from typing import List
from events.command_tower.models import TaskDefinition, LoopRoundContext
from events.command_tower.task_registrar import TaskRegistrar


class LoopController:
    """
    循环任务管理器
    管理循环任务的执行、轮次上下文和循环条件评估
    """
    
    def __init__(self, db_client, task_registrar):
        """
        初始化循环任务管理器
        
        Args:
            db_client: 数据库客户端，需支持相关查询和操作方法
            task_registrar: 任务注册器实例，用于注册新任务
        """
        self.db = db_client
        self.task_registrar = task_registrar
    
    def create_loop_context(self, trace_id: str, round_index: int, 
                           input_params: dict) -> LoopRoundContext:
        """
        创建循环轮次上下文
        
        Args:
            trace_id: 跟踪ID
            round_index: 轮次索引
            input_params: 输入参数
            
        Returns:
            创建的循环轮次上下文
        """
        context = LoopRoundContext(
            trace_id=trace_id,
            round_index=round_index,
            input_params=input_params,
            should_continue=True,
            created_at=datetime.now(timezone.utc)
        )
        
        # 保存上下文到数据库
        self.db.insert_loop_round_context(context)
        
        return context
    
    def update_loop_context(self, context: LoopRoundContext):
        """
        更新循环轮次上下文
        
        Args:
            context: 更新后的循环轮次上下文
        """
        self.db.update_loop_round_context(context)
    
    def evaluate_loop_continue(self, trace_id: str) -> bool:
        """
        评估循环是否需要继续
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            是否需要继续循环
        """
        # 获取循环任务定义
        root_task = self.db.get_root_task(trace_id)
        if not root_task:
            return False
        
        definition = self.db.get_task_definition(root_task.definition_id)
        if not definition or definition.schedule_type != "LOOP":
            return False
        
        # 获取当前轮次上下文
        current_round = self.db.get_current_loop_round(trace_id)
        context = self.db.get_loop_round_context(trace_id, current_round)
        
        if not context:
            return False
        
        # 检查上下文的should_continue标志
        if not context.should_continue:
            return False
        
        # 检查最大轮次限制
        loop_config = definition.loop_config or {}
        max_rounds = loop_config.get("max_rounds", 5)
        
        return current_round < max_rounds
    
    def register_next_round_tasks(self, trace_id: str, 
                                 current_round: int, 
                                 next_input_params: dict) -> List[str]:
        """
        注册新一轮的子任务
        
        Args:
            trace_id: 跟踪ID
            current_round: 当前轮次索引
            next_input_params: 下一轮的输入参数
            
        Returns:
            注册成功的任务ID列表
        """
        # 创建下一轮的上下文
        next_round = current_round + 1
        context = self.create_loop_context(
            trace_id=trace_id,
            round_index=next_round,
            input_params=next_input_params
        )
        
        # 获取根任务
        root_task = self.db.get_root_task(trace_id)
        if not root_task:
            return []
        
        # 这里应该调用Agent生成下一轮的任务拓扑
        # 示例代码：实际实现中应该调用Agent的接口获取任务列表
        # tasks = agent.generate_next_round_tasks(trace_id, context)
        
        # 为简化示例，这里返回空列表
        # 实际实现中应该使用self.task_registrar.register_tasks(tasks)注册任务
        return []
    
    def get_loop_history(self, trace_id: str) -> List[LoopRoundContext]:
        """
        获取循环任务的历史轮次上下文
        
        Args:
            trace_id: 跟踪ID
            
        Returns:
            历史轮次上下文列表，按轮次索引排序
        """
        return self.db.query("SELECT * FROM loop_round_contexts WHERE trace_id = ? ORDER BY round_index", trace_id)
