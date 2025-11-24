from thespian.actors import ActorTypeDispatcher, ActorAddress
import logging
from typing import Dict, Any, List
from new.common.messages.agent_messages import TaskGroupRequest, TaskSpec

logger = logging.getLogger(__name__)

class TaskPlanningActor(ActorTypeDispatcher):
    """
    任务规划协调Actor：负责处理任务规划和子任务创建
    遵循actor模型的异步特性，接收规划请求，执行规划，并创建子任务
    """
    
    def __init__(self):
        super().__init__()
        self._task_coordinator = None
        self._task_group_aggregator_class = None
        self._map_capability_to_task_type = None
        
    def receiveMsg_Dict(self, message: Dict[str, Any], sender: ActorAddress):
        """
        接收任务规划请求消息
        message格式: {
            'type': 'plan_tasks',
            'parent_task_id': str,
            'selected_node_id': str,
            'context': dict,
            'original_sender': ActorAddress,
            'task_coordinator': object,
            'task_group_aggregator_class': class,
            'map_capability_func': function
        }
        """
        try:
            if message.get('type') != 'plan_tasks':
                logger.warning(f"未知消息类型: {message.get('type')}")
                return
                
            # 提取必要参数
            parent_task_id = message['parent_task_id']
            selected_node_id = message['selected_node_id']
            context = message['context']
            original_sender = message['original_sender']
            
            # 存储任务协调器和相关函数引用
            self._task_coordinator = message['task_coordinator']
            self._task_group_aggregator_class = message['task_group_aggregator_class']
            self._map_capability_to_task_type = message['map_capability_func']
            
            # 执行任务规划
            self._execute_task_planning(parent_task_id, selected_node_id, context, original_sender)
            
        except Exception as e:
            logger.error(f"处理任务规划请求时出错: {e}", exc_info=True)
            # 可以选择向发送者报告错误
            
    def _execute_task_planning(self, parent_task_id: str, selected_node_id: str, 
                              context: Dict, original_sender: ActorAddress):
        """
        执行任务规划和子任务创建
        """
        try:
            # 生成任务执行计划
            plan = self._task_coordinator.plan_subtasks(selected_node_id, context)
            
            # 创建子任务定义列表
            task_specs = []
            for i, step in enumerate(plan):
                child_cap = step["node_id"]
                child_ctx = self._task_coordinator.resolve_context(
                    {**context, **step.get("intent_params", {})}, 
                    selected_node_id
                )
                child_task_id = f"{parent_task_id}.child_{i}"
                
                # 创建TaskSpec对象
                task_spec = TaskSpec(
                    task_id=child_task_id,
                    type=self._map_capability_to_task_type(child_cap),
                    parameters={
                        "context": child_ctx,
                        "agent_id": step["node_id"],
                        "capability": child_cap
                    }
                )
                task_specs.append(task_spec)
            
            # 创建任务组聚合器Actor
            task_group_aggregator = self.createActor(self._task_group_aggregator_class)
            
            # 构造任务组请求
            task_group_request = TaskGroupRequest(
                source=self.myAddress,
                destination=task_group_aggregator,
                reply_to=original_sender,  # 回复给原始发送者
                group_id=parent_task_id,
                tasks=task_specs
            )
            
            # 发送任务组请求给聚合器
            self.send(task_group_aggregator, task_group_request)
            
            # 向原始发送者报告任务组已创建
            report_message = {
                "type": "task_group_created",
                "parent_task_id": parent_task_id,
                "task_count": len(task_specs),
                "aggregator": "TaskGroupAggregatorActor"
            }
            self.send(original_sender, report_message)
            
            logger.info(f"任务组创建成功，父任务ID: {parent_task_id}, 子任务数量: {len(task_specs)}")
            
        except Exception as e:
            logger.error(f"执行任务规划时出错: {e}", exc_info=True)
            # 可以向原始发送者报告错误
            error_message = {
                "type": "task_planning_error",
                "parent_task_id": parent_task_id,
                "error": str(e)
            }
            self.send(original_sender, error_message)
