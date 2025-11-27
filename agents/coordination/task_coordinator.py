"""
任务协调器
负责任务的协调、子任务生成与管理
支持任务分配、执行状态跟踪和结果聚合
"""
import logging
from typing import Any, Dict, List, Set, Optional
from thespian.actors import ActorAddress

# 导入新的模块
from capabilities.routing.task_planner import TaskPlanner
from capabilities.routing.context_resolver import ContextResolver
from capabilities.result_aggregation.result_aggregation import ResultAggregator
# 导入任务状态相关定义
from capabilities.routing.task_status import TaskStatus, TaskDependency, TaskResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaskCoordinator:
    """任务协调器"""
    
    def __init__(self):
        """初始化任务协调器"""
        self._active_tasks: Dict[str, Dict] = {}
        self._subtasks: Dict[str, List[Dict]] = {}
        self._task_dependencies: Dict[str, List[str]] = {}
        self._pending_results: Dict[str, Dict] = {}
        self._max_subtasks_per_task = 20  # 每个任务最多子任务数
        
        # 初始化任务规划器和上下文解析器
        self._task_planner = TaskPlanner()
        self._context_resolver = ContextResolver()
    
    def is_leaf_task(self, agent_id: str, context: Dict) -> bool:
        """
        判断是否为叶子任务
        
        Args:
            agent_id: Agent ID
            context: 任务上下文
            
        Returns:
            是否为叶子任务
        """
        # 简单实现：如果任务类型包含"leaf"则认为是叶子任务
        task_type = context.get("task_type", "")
        return "leaf" in task_type.lower()
    
    def create_task(self, task_id: str, task_type: str, context: Dict,
                   parent_task_id: Optional[str] = None) -> Dict:
        """
        创建新任务
        
        Args:
            task_id: 任务ID
            task_type: 任务类型
            context: 任务上下文
            parent_task_id: 父任务ID
            
        Returns:
            创建的任务信息
        """
        # 检查任务是否已存在
        if task_id in self._active_tasks:
            logger.warning(f"Task {task_id} already exists")
            return self._active_tasks[task_id]
        
        # 创建任务
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "context": context,
            "parent_task_id": parent_task_id,
            "status": "created",
            "created_at": "now",  # 实际应使用时间戳
            "updated_at": "now",
            "subtasks_count": 0,
            "completed_subtasks": 0,
            "failed_subtasks": 0
        }
        
        # 保存任务
        self._active_tasks[task_id] = task
        
        # 如果有父任务，建立关联
        if parent_task_id:
            if parent_task_id not in self._subtasks:
                self._subtasks[parent_task_id] = []
            self._subtasks[parent_task_id].append(task)
            
            if task_id not in self._task_dependencies:
                self._task_dependencies[task_id] = []
            self._task_dependencies[task_id].append(parent_task_id)
            
            # 更新父任务的子任务计数
            if parent_task_id in self._active_tasks:
                self._active_tasks[parent_task_id]["subtasks_count"] += 1
                self._active_tasks[parent_task_id]["updated_at"] = "now"
        
        logger.info(f"Created task {task_id} of type {task_type}")
        return task
    
    def generate_subtasks(self, parent_task_id: str, task_type: str,
                         subtask_configs: List[Dict]) -> List[Dict]:
        """
        为父任务生成子任务
        
        Args:
            parent_task_id: 父任务ID
            task_type: 子任务类型
            subtask_configs: 子任务配置列表
            
        Returns:
            生成的子任务列表
        """
        # 检查父任务是否存在
        if parent_task_id not in self._active_tasks:
            logger.error(f"Parent task {parent_task_id} not found")
            raise ValueError(f"Parent task {parent_task_id} not found")
        
        # 检查子任务数量限制
        if len(subtask_configs) > self._max_subtasks_per_task:
            logger.warning(f"Too many subtasks ({len(subtask_configs)}), maximum is {self._max_subtasks_per_task}")
            subtask_configs = subtask_configs[:self._max_subtasks_per_task]
        
        # 生成子任务
        generated_subtasks = []
        for config in subtask_configs:
            subtask_id = config.get("subtask_id") or f"subtask_{parent_task_id}_{len(self._subtasks.get(parent_task_id, [])) + 1}"
            context = config.get("context", {})
            agent_id = config.get("agent_id")
            capability = config.get("capability")
            
            # 创建子任务
            subtask = self.create_task(
                task_id=subtask_id,
                task_type=task_type,
                context=context,
                parent_task_id=parent_task_id
            )
            
            # 添加额外信息
            subtask["agent_id"] = agent_id
            subtask["capability"] = capability
            
            generated_subtasks.append(subtask)
        
        # 更新父任务状态
        self._active_tasks[parent_task_id]["status"] = "processing"
        self._active_tasks[parent_task_id]["updated_at"] = "now"
        
        logger.info(f"Generated {len(generated_subtasks)} subtasks for parent task {parent_task_id}")
        return generated_subtasks
    
    def update_task_status(self, task_id: str, status: str, 
                          result: Optional[Dict] = None,
                          error: Optional[str] = None) -> Dict:
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态 (created, processing, completed, failed)
            result: 任务结果 (如果完成)
            error: 错误信息 (如果失败)
            
        Returns:
            更新后的任务信息
        """
        # 检查任务是否存在
        if task_id not in self._active_tasks:
            logger.error(f"Task {task_id} not found for status update")
            return None
        
        task = self._active_tasks[task_id]
        task["status"] = status
        task["updated_at"] = "now"
        
        # 处理完成状态
        if status == "completed" and result is not None:
            task["result"] = result
            
            # 处理父任务的子任务完成情况
            if task.get("parent_task_id"):
                parent_id = task["parent_task_id"]
                if parent_id in self._active_tasks:
                    self._active_tasks[parent_id]["completed_subtasks"] += 1
                    
                    # 检查父任务是否所有子任务都已完成
                    if self._active_tasks[parent_id]["completed_subtasks"] == \
                       self._active_tasks[parent_id]["subtasks_count"]:
                        # 所有子任务都已完成，尝试完成父任务
                        self._try_complete_parent_task(parent_id)
        
        # 处理失败状态
        elif status == "failed" and error is not None:
            task["error"] = error
            
            # 处理父任务的子任务失败情况
            if task.get("parent_task_id"):
                parent_id = task["parent_task_id"]
                if parent_id in self._active_tasks:
                    self._active_tasks[parent_id]["failed_subtasks"] += 1
        
        logger.info(f"Updated task {task_id} status to {status}")
        return task
    
    def _try_complete_parent_task(self, parent_task_id: str):
        """
        尝试完成父任务
        当所有子任务完成时，汇总结果并更新父任务状态
        """
        if parent_task_id not in self._active_tasks:
            return
        
        parent_task = self._active_tasks[parent_task_id]
        
        # 收集所有子任务结果
        subtask_results = {}
        has_errors = False
        
        for subtask in self._subtasks.get(parent_task_id, []):
            subtask_id = subtask["task_id"]
            if subtask_id in self._active_tasks:
                subtask_info = self._active_tasks[subtask_id]
                if subtask_info["status"] == "completed" and "result" in subtask_info:
                    subtask_results[subtask_id] = subtask_info["result"]
                elif subtask_info["status"] == "failed":
                    has_errors = True
                    break
        
        # 如果有子任务失败，父任务可能需要重新评估
        if has_errors:
            logger.warning(f"Parent task {parent_task_id} has failed subtasks, not completing")
            return
        
        # 聚合子任务结果
        aggregated_result = self._aggregate_subtask_results(parent_task, subtask_results)
        
        # 更新父任务状态为完成
        self.update_task_status(parent_task_id, "completed", aggregated_result)
        
        logger.info(f"Parent task {parent_task_id} completed with aggregated results")
    
    def _aggregate_subtask_results(self, parent_task: Dict, subtask_results: Dict) -> Dict:
        """
        聚合子任务结果 - 使用ResultAggregator进行聚合
        """
        # 转换subtask_results格式以匹配ResultAggregator的要求
        subtasks = []
        for subtask_id, result in subtask_results.items():
            subtask = {
                'task_id': subtask_id,
                'status': 'completed',
                'result': result
            }
            subtasks.append(subtask)
        
        return ResultAggregator.aggregate_subtask_results(parent_task, subtasks)
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息，如果不存在则返回None
        """
        return self._active_tasks.get(task_id)
    
    def get_subtasks(self, parent_task_id: str) -> List[Dict]:
        """
        获取指定父任务的所有子任务
        
        Args:
            parent_task_id: 父任务ID
            
        Returns:
            子任务列表
        """
        subtasks = []
        if parent_task_id in self._subtasks:
            for subtask in self._subtasks[parent_task_id]:
                subtask_id = subtask["task_id"]
                if subtask_id in self._active_tasks:
                    subtasks.append(self._active_tasks[subtask_id])
        
        return subtasks
    
    def get_active_tasks(self, task_type: Optional[str] = None) -> List[Dict]:
        """
        获取所有活跃任务，可按类型过滤
        
        Args:
            task_type: 任务类型，为None时返回所有任务
            
        Returns:
            活跃任务列表
        """
        if task_type is None:
            return list(self._active_tasks.values())
        
        return [task for task in self._active_tasks.values() 
                if task["task_type"] == task_type]
    
    def assign_task_to_agent(self, task_id: str, agent_id: str,
                           agent_address: Optional[ActorAddress] = None) -> bool:
        """
        将任务分配给智能体
        
        Args:
            task_id: 任务ID
            agent_id: 智能体ID
            agent_address: 智能体地址
            
        Returns:
            分配是否成功
        """
        if task_id not in self._active_tasks:
            logger.error(f"Task {task_id} not found for agent assignment")
            return False
        
        task = self._active_tasks[task_id]
        task["agent_id"] = agent_id
        task["agent_address"] = agent_address
        task["updated_at"] = "now"
        
        logger.info(f"Assigned task {task_id} to agent {agent_id}")
        return True
    
    def cancel_task(self, task_id: str, reason: Optional[str] = None) -> bool:
        """
        取消任务及其所有子任务
        
        Args:
            task_id: 任务ID
            reason: 取消原因
            
        Returns:
            取消是否成功
        """
        if task_id not in self._active_tasks:
            logger.error(f"Task {task_id} not found for cancellation")
            return False
        
        # 取消所有子任务
        for subtask in self._subtasks.get(task_id, []):
            subtask_id = subtask["task_id"]
            self.cancel_task(subtask_id, reason)
        
        # 更新当前任务状态为失败
        cancel_reason = reason or "Task cancelled by user or system"
        self.update_task_status(task_id, "failed", error=cancel_reason)
        
        logger.info(f"Cancelled task {task_id} and its subtasks: {cancel_reason}")
        return True
    
    def cleanup_completed_tasks(self, max_age_seconds: int = 3600):
        """
        清理已完成的任务
        
        Args:
            max_age_seconds: 保留的最大时间（秒）
        """
        # 注意：这里简化了实现，实际应该基于时间戳进行清理
        completed_tasks = [task_id for task_id, task in self._active_tasks.items() 
                          if task["status"] in ("completed", "failed")]
        
        for task_id in completed_tasks:
            # 检查是否有未完成的子任务（理论上不应该有）
            subtasks = self.get_subtasks(task_id)
            if any(subtask["status"] not in ("completed", "failed") for subtask in subtasks):
                continue
            
            # 删除任务
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]
            
            if task_id in self._subtasks:
                del self._subtasks[task_id]
            
            if task_id in self._task_dependencies:
                del self._task_dependencies[task_id]
            
            logger.info(f"Cleaned up completed task {task_id}")
    
    def plan_subtasks(self, parent_agent_id: str, context: Dict[str, Any]) -> List[Dict]:
        """
        生成任务执行计划
        
        Args:
            parent_agent_id: 父Agent ID
            context: 任务上下文
            
        Returns:
            执行计划
        """
        return self._task_planner.plan_subtasks(parent_agent_id, context)
    
    def resolve_context(self, context: Dict[str, Any], agent_id: str) -> Dict[str, Any]:
        """
        解析任务上下文
        
        Args:
            context: 原始上下文
            agent_id: 当前Agent ID
            
        Returns:
            解析后的上下文
        """
        return self._context_resolver.resolve_context(context, agent_id)
    
    def needs_parallel_execution(self, context: Dict[str, Any]) -> bool:
        """
        判断任务是否需要并行执行
        
        Args:
            context: 任务上下文
            
        Returns:
            是否需要并行执行的布尔值
        """
        # 实现逻辑可以根据上下文内容判断是否需要并行
        # 这里提供一个示例实现，可以根据实际需求扩展
        
        # 1. 检查是否有明确的并行执行标记
        if context.get('parallel', False):
            return True
        
        # 2. 检查任务类型是否适合并行
        task_type = context.get('task_type')
        parallel_task_types = ['batch_processing', 'data_analysis', 'multiple_api_calls']
        if task_type in parallel_task_types:
            return True
        
        # 3. 检查是否有多个独立的子任务需求
        if isinstance(context.get('subtasks'), list) and len(context['subtasks']) > 1:
            return True
        
        # 4. 检查任务复杂度或数据量
        if context.get('data_size', 0) > 1000:
            return True
        
        # 默认不并行
        return False
    
    def get_task_statistics(self) -> Dict:
        """
        获取任务统计信息
        
        Returns:
            任务统计信息
        """
        stats = {
            "total_tasks": len(self._active_tasks),
            "by_status": {},
            "by_type": {}
        }
        
        # 按状态统计
        for task in self._active_tasks.values():
            status = task["status"]
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
            
            task_type = task["task_type"]
            stats["by_type"][task_type] = stats["by_type"].get(task_type, 0) + 1
        
        # 计算成功率
        total_completed = stats["by_status"].get("completed", 0)
        total_failed = stats["by_status"].get("failed", 0)
        total_processed = total_completed + total_failed
        
        if total_processed > 0:
            stats["success_rate"] = (total_completed / total_processed) * 100
        else:
            stats["success_rate"] = 0
        
        return stats
