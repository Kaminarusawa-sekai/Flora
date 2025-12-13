from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import uuid4
from interaction.common.task_execution import TaskExecutionContextDTO
from interaction.common.base import ExecutionStatus, ExecutionLogEntry
from interaction.common.task_draft import ScheduleDTO

class TaskStorage:
    """任务存储类，用于从外部系统获取任务数据"""
    
    def __init__(self):
        # 模拟存储，使用字典存储任务，key为task_id
        self._tasks: Dict[str, TaskExecutionContextDTO] = {}
        # 初始化一些模拟数据
        self._initialize_mock_data()
    
    def _initialize_mock_data(self):
        """初始化模拟数据"""
        # 创建一些模拟任务
        mock_tasks = [
            {
                "draft_id": "draft_001",
                "task_type": "web_crawler",
                "title": "爬取京东商品数据",
                "created_by": "user_001",
                "execution_status": ExecutionStatus.COMPLETED,
                "control_status": "NORMAL",
                "tags": ["爬虫", "电商", "京东"],
                "result_data": {"success": True, "items_count": 100}
            },
            {
                "draft_id": "draft_002",
                "task_type": "data_analysis",
                "title": "销售数据分析",
                "created_by": "user_001",
                "execution_status": ExecutionStatus.RUNNING,
                "control_status": "NORMAL",
                "tags": ["数据分析", "销售"],
                "logs": [ExecutionLogEntry(message="任务开始执行"), ExecutionLogEntry(message="正在处理数据")]
            },
            {
                "draft_id": "draft_003",
                "task_type": "email_sender",
                "title": "发送营销邮件",
                "created_by": "user_002",
                "execution_status": ExecutionStatus.FAILED,
                "control_status": "NORMAL",
                "tags": ["邮件", "营销"],
                "error_detail": {"code": "SMTP_ERROR", "message": "无法连接到邮件服务器"}
            },
            {
                "draft_id": "draft_004",
                "task_type": "web_crawler",
                "title": "爬取淘宝商品数据",
                "created_by": "user_001",
                "execution_status": ExecutionStatus.NOT_STARTED,
                "control_status": "NORMAL",
                "tags": ["爬虫", "电商", "淘宝"]
            },
            {
                "draft_id": "draft_005",
                "task_type": "file_processing",
                "title": "处理Excel文件",
                "created_by": "user_002",
                "execution_status": ExecutionStatus.COMPLETED,
                "control_status": "NORMAL",
                "tags": ["文件处理", "Excel"],
                "result_data": {"success": True, "processed_files": 5}
            }
        ]
        
        # 将模拟任务添加到存储中
        for task_data in mock_tasks:
            task = TaskExecutionContextDTO(**task_data)
            self._tasks[task.task_id] = task
    
    def save_execution_context(self, context: TaskExecutionContextDTO) -> str:
        """保存任务执行上下文
        
        Args:
            context: 任务执行上下文
            
        Returns:
            str: 任务ID
        """
        self._tasks[context.task_id] = context
        return context.task_id
    
    def get_execution_context(self, task_id: str) -> Optional[TaskExecutionContextDTO]:
        """根据任务ID获取任务执行上下文
        
        Args:
            task_id: 任务ID
            
        Returns:
            Optional[TaskExecutionContextDTO]: 任务执行上下文，如果不存在则返回None
        """
        return self._tasks.get(task_id)
    
    def update_execution_context(self, context: TaskExecutionContextDTO) -> bool:
        """更新任务执行上下文
        
        Args:
            context: 任务执行上下文
            
        Returns:
            bool: 更新是否成功
        """
        if context.task_id not in self._tasks:
            return False
        self._tasks[context.task_id] = context
        return True
    
    def list_execution_contexts(self, user_id: str, filters: Dict[str, Any] = None) -> List[TaskExecutionContextDTO]:
        """根据用户ID和过滤条件列出任务执行上下文
        
        Args:
            user_id: 用户ID
            filters: 过滤条件，支持以下过滤字段：
                - task_type: 任务类型
                - execution_status: 执行状态
                - control_status: 控制状态
                - tags: 标签列表（支持包含任意标签）
                - task_id: 任务ID（精确匹配）
                - time_range: 时间范围（如 yesterday, today, this_week）
                - page: 页码（默认1）
                - page_size: 每页大小（默认10）
                - sort_by: 排序字段（默认created_at）
                - sort_order: 排序顺序（asc或desc，默认desc）
                
        Returns:
            List[TaskExecutionContextDTO]: 任务执行上下文列表
        """
        # 初始化过滤条件
        filters = filters or {}
        
        # 先过滤出用户自己的任务
        user_tasks = [task for task in self._tasks.values() if task.created_by == user_id]
        
        # 应用过滤条件
        filtered_tasks = []
        for task in user_tasks:
            # 检查是否符合所有过滤条件
            match = True
            
            # 检查任务ID
            if "task_id" in filters and task.task_id != filters["task_id"]:
                match = False
            
            # 检查任务类型
            if "task_type" in filters and task.task_type != filters["task_type"]:
                match = False
            
            # 检查执行状态
            if "execution_status" in filters and task.execution_status != filters["execution_status"]:
                match = False
            
            # 检查控制状态
            if "control_status" in filters and task.control_status != filters["control_status"]:
                match = False
            
            # 检查标签（支持包含任意标签）
            if "tags" in filters:
                if not set(filters["tags"]).intersection(set(task.tags)):
                    match = False
            
            # 检查时间范围（简化实现）
            if "time_range" in filters:
                # 这里可以根据实际需求实现更复杂的时间范围过滤
                pass
            
            if match:
                filtered_tasks.append(task)
        
        # 排序
        sort_by = filters.get("sort_by", "created_at")
        sort_order = filters.get("sort_order", "desc")
        
        # 执行排序
        filtered_tasks.sort(
            key=lambda x: getattr(x, sort_by) if hasattr(x, sort_by) else x.created_at,
            reverse=(sort_order == "desc")
        )
        
        # 分页
        page = int(filters.get("page", 1))
        page_size = int(filters.get("page_size", 10))
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        
        return filtered_tasks[start_index:end_index]
    
    def delete_execution_context(self, task_id: str, user_id: str) -> bool:
        """删除任务执行上下文
        
        Args:
            task_id: 任务ID
            user_id: 用户ID，用于验证权限
            
        Returns:
            bool: 删除是否成功
        """
        if task_id not in self._tasks:
            return False
        
        # 验证用户权限
        if self._tasks[task_id].created_by != user_id:
            return False
        
        del self._tasks[task_id]
        return True
    
    def add_execution_log(self, task_id: str, level: str, message: str) -> bool:
        """添加执行日志
        
        Args:
            task_id: 任务ID
            level: 日志级别
            message: 日志消息
            
        Returns:
            bool: 添加是否成功
        """
        if task_id not in self._tasks:
            return False
        
        log_entry = ExecutionLogEntry(level=level, message=message)
        self._tasks[task_id].logs.append(log_entry)
        return True
    
    def update_task_status(self, task_id: str, execution_status: ExecutionStatus, 
                          control_status: Optional[str] = None) -> bool:
        """更新任务状态
        
        Args:
            task_id: 任务ID
            execution_status: 执行状态
            control_status: 控制状态（可选）
            
        Returns:
            bool: 更新是否成功
        """
        if task_id not in self._tasks:
            return False
        
        task = self._tasks[task_id]
        task.execution_status = execution_status
        if control_status is not None:
            task.control_status = control_status
        
        self._tasks[task_id] = task
        return True
    
    def get_task_count(self, user_id: str, filters: Dict[str, Any] = None) -> int:
        """获取任务数量
        
        Args:
            user_id: 用户ID
            filters: 过滤条件
            
        Returns:
            int: 任务数量
        """
        tasks = self.list_execution_contexts(user_id, filters)
        return len(tasks)
