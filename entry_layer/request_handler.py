# request_handler.py
"""
Flora多智能体协作系统 - 请求处理器

负责处理来自API服务器的请求，协调内部服务调用，并返回处理结果
"""

import logging
from typing import Dict, Any, Optional, Union, List
from datetime import datetime

logger = logging.getLogger(__name__)


class RequestHandler:
    """
    请求处理器类，负责协调各模块处理具体业务逻辑
    """
    
    def __init__(self, tenant_router=None, config: Optional[Dict[str, Any]] = None):
        """
        初始化请求处理器
        
        Args:
            tenant_router: 租户路由分发器实例
            config: 处理器配置字典
        """
        self.config = config or {}
        self.tenant_router = tenant_router
        
        # 注册操作处理器
        self._operation_handlers = {
            'create_task': self._handle_create_task,
            'create_task_and_comment': self._handle_create_task_and_comment,
            'get_task': self._handle_get_task,
            'update_task': self._handle_update_task,
            'delete_task': self._handle_delete_task,
            'get_agent': self._handle_get_agent,
            'add_task_comment': self._handle_add_task_comment,
            'get_task_current_execution': self._handle_get_task_current_execution,
            'get_task_plan': self._handle_get_task_plan,
            'get_task_people': self._handle_get_task_persons,
            'get_task_leaf_agents': self._handle_get_task_leaf_agents,
            'get_task_execution_path': self._handle_get_task_execution_path,
            'get_task_progress': self._handle_get_task_progress,
        }
    
    async def handle(
        self,
        operation: str,
        data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        统一请求处理入口
        
        Args:
            operation: 操作类型
            data: 请求数据
            context: 请求上下文
            **kwargs: 额外参数
            
        Returns:
            处理结果
            
        Raises:
            ValueError: 当操作类型无效时
        """
        # 记录请求日志
        request_id = context.get('request_id', 'unknown')
        tenant_id = context.get('tenant_id', 'unknown')
        user_id = context.get('user_id', 'unknown')
        
        logger.info(
            f"Request received: {operation} | "
            f"Request ID: {request_id} | "
            f"Tenant: {tenant_id} | "
            f"User: {user_id}"
        )
        
        # 验证操作类型
        if operation not in self._operation_handlers:
            raise ValueError(f"Invalid operation: {operation}")
        
        # 获取对应的处理器
        handler = self._operation_handlers[operation]
        
        try:
            # 调用具体的处理器
            result = await handler(data, context, **kwargs)
            
            # 记录成功日志
            logger.info(
                f"Request completed: {operation} | "
                f"Request ID: {request_id}"
            )
            
            return result
            
        except Exception as e:
            # 记录错误日志
            logger.error(
                f"Request failed: {operation} | "
                f"Request ID: {request_id} | "
                f"Error: {str(e)}",
                exc_info=True
            )
            
            # 重新抛出异常，让上层处理
            raise
    
    async def _handle_create_task(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理创建任务请求
        
        Args:
            data: 任务数据
            context: 请求上下文
            
        Returns:
            创建的任务信息
        """
        # 从租户路由获取对应的任务服务
        tenant_id = context.get('tenant_id')
        task_id = f"task-{datetime.now().timestamp()}"
        
        # 创建任务数据
        task = {
            'id': task_id,
            'name': data.get('name', 'Unnamed Task'),
            'description': data.get('description', ''),
            'status': 'pending',
            'priority': data.get('priority', 'medium'),
            'created_at': datetime.now().isoformat(),
            'tenant_id': tenant_id,
            'created_by': context.get('user_id')
        }
        
        # 尝试获取任务服务创建任务
        if self.tenant_router:
            task_service = await self.tenant_router.get_service(
                tenant_id=tenant_id,
                service_type='task'
            )
            # 调用任务服务创建任务
            # 这里是模拟实现，实际应该调用真实的服务
            
            # 记录任务创建事件
            event_actor = await self.tenant_router.get_service(tenant_id, 'event_actor')
            # 使用store_event方法存储事件
            event_actor.store_event(
                event_type="task_created",
                data={
                    "task_id": task_id,
                    "task": task,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        return task

    async def _handle_create_task_and_comment(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理创建任务并追加评论请求
        
        Args:
            data: 包含任务数据和评论内容的字典
            context: 请求上下文
            
        Returns:
            包含创建的任务信息和评论信息的字典
        """
        # 创建任务
        task = await self._handle_create_task(data, context, **kwargs)
        
        # 追加评论
        comment_data = {
            'comment': data.get('comment', '')
        }
        
        # 调用add_task_comment处理
        comment_result = await self._handle_add_task_comment(
            comment_data, 
            context, 
            task_id=task['id'], 
            **kwargs
        )
        
        return {
            'task': task,
            'comment': comment_result.get('comment'),
            'success': True,
            'message': '任务和评论创建成功'
        }
    
    async def _handle_get_task(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理获取任务请求
        
        Args:
            data: 请求数据（通常为空）
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            任务详细信息
        """
        tenant_id = context.get('tenant_id')
        
        # 模拟返回任务信息
        return {
            'id': task_id,
            'name': f'Task {task_id}',
            'description': 'Task description',
            'status': 'in_progress',
            'priority': 'medium',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'tenant_id': tenant_id
        }
    
    async def _handle_update_task(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理更新任务请求
        
        Args:
            data: 更新的数据
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            更新后的任务信息
        """
        tenant_id = context.get('tenant_id')
        
        # 模拟更新任务
        updated_task = {
            'id': task_id,
            'name': data.get('name', f'Task {task_id}'),
            'description': data.get('description', 'Updated description'),
            'status': data.get('status', 'in_progress'),
            'priority': data.get('priority', 'medium'),
            'updated_at': datetime.now().isoformat(),
            'tenant_id': tenant_id
        }
        
        return updated_task
    
    async def _handle_delete_task(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理删除任务请求
        
        Args:
            data: 请求数据（通常为空）
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            删除结果
        """
        # 模拟删除任务
        return {
            'success': True,
            'message': f'Task {task_id} deleted successfully',
            'task_id': task_id
        }
    
    async def _handle_get_agent(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        agent_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理获取智能体信息请求
        
        Args:
            data: 请求数据（通常为空）
            context: 请求上下文
            agent_id: 智能体ID
            
        Returns:
            智能体信息
        """
        # 从租户路由获取对应的智能体服务
        tenant_id = context.get('tenant_id')
        if self.tenant_router:
            agent_service = await self.tenant_router.get_service(
                tenant_id=tenant_id,
                service_type='agent'
            )
            # 这里应该调用真实的服务
            pass
        
        # 模拟返回智能体信息
        return {
            'id': agent_id,
            'name': f'Agent {agent_id}',
            'type': 'general',
            'version': '1.0.0',
            'status': 'online',
            'capabilities': ['task_execution', 'data_analysis'],
            'tenant_id': tenant_id,
            'last_active': datetime.now().isoformat()
        }
    
    async def _handle_add_task_comment(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理为任务追加评论请求
        
        Args:
            data: 请求数据
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            评论添加结果
        """
        # 获取评论内容
        content = data.get('content', '')
        if not content:
            return {
                'success': False,
                'message': '评论内容不能为空'
            }
        
        # 获取当前用户
        user_id = context.get('user_id', 'system_user')
        
        # 构建评论数据
        comment_data = {
            'task_id': task_id,
            'comment_id': f'comment_{int(datetime.now().timestamp() * 1000)}',
            'content': content,
            'user': user_id,
            'timestamp': datetime.now().isoformat()
        }
        
        # 记录评论添加事件
        tenant_id = context.get('tenant_id')
        if self.tenant_router:
            event_actor = await self.tenant_router.get_service(tenant_id, 'event_actor')
            # 使用store_event方法存储事件
            event_actor.store_event(
                event_type="comment_added",
                data=comment_data
            )
        
        # 返回添加结果
        return {
            'success': True,
            'data': comment_data,
            'message': '评论添加成功'
        }
    
    async def _handle_get_task_current_execution(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理获取任务当前执行内容请求
        
        Args:
            data: 请求数据（通常为空）
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            任务当前执行内容
        """
        # 获取EventActor服务
        tenant_id = context.get('tenant_id')
        if self.tenant_router:
            event_actor = await self.tenant_router.get_service(tenant_id, 'event_actor')
            
            # 从事件历史中获取最新的任务执行事件
            await event_actor._get_event_history(limit=10, task_id=task_id)
        
        # 模拟返回任务当前执行内容
        return {
            'success': True,
            'data': {
                'task_id': task_id,
                'current_step': '数据清洗与预处理',
                'description': '正在使用Pandas清洗和预处理销售数据，包括缺失值填充、异常值处理和数据转换',
                'current_operator': 'data_processing_agent_001',
                'start_time': datetime.now().isoformat(),
                'status': 'running',
                'progress': 35
            },
            'message': '获取任务当前执行内容成功'
        }
    
    async def _handle_get_task_plan(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理获取任务计划执行的n项内容请求
        
        Args:
            data: 请求数据（包含计划数量等）
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            任务计划执行的n项内容
        """
        # 获取EventActor服务
        tenant_id = context.get('tenant_id')
        event_actor = await self.tenant_router.get_service(tenant_id, 'event_actor')
        
        # 从事件历史中获取任务计划相关事件
        events = await event_actor._get_event_history(limit=50, task_id=task_id)
        
        # 模拟返回任务计划执行的n项内容
        return {
            'success': True,
            'data': {
                'task_id': task_id,
                'plan_items': [
                    {
                        'id': 'plan_item_001',
                        'step_name': '数据收集',
                        'description': '收集用户的历史购买记录和行为数据',
                        'assignee': 'data_collection_agent_001',
                        'status': 'completed',
                        'start_time': '2023-05-15T10:00:00Z',
                        'end_time': '2023-05-15T10:30:00Z'
                    },
                    {
                        'id': 'plan_item_002',
                        'step_name': '数据清洗与预处理',
                        'description': '清洗和预处理收集到的数据，包括缺失值填充、异常值处理和数据转换',
                        'assignee': 'data_processing_agent_001',
                        'status': 'running',
                        'start_time': '2023-05-15T10:30:00Z'
                    },
                    {
                        'id': 'plan_item_003',
                        'step_name': '模型训练',
                        'description': '使用处理后的数据训练推荐模型',
                        'assignee': 'model_training_agent_001',
                        'status': 'pending'
                    },
                    {
                        'id': 'plan_item_004',
                        'step_name': '模型评估',
                        'description': '评估训练好的推荐模型性能',
                        'assignee': 'model_evaluation_agent_001',
                        'status': 'pending'
                    },
                    {
                        'id': 'plan_item_005',
                        'step_name': '结果生成',
                        'description': '基于模型生成推荐结果并保存',
                        'assignee': 'result_generation_agent_001',
                        'status': 'pending'
                    }
                ]
            },
            'message': '获取任务计划执行内容成功'
        }
    
    async def _handle_get_task_persons(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理获取任务下人员情况请求
        
        Args:
            data: 请求数据（通常为空）
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            任务下人员情况
        """
        # 获取EventActor服务
        tenant_id = context.get('tenant_id')
        event_actor = await self.tenant_router.get_service(tenant_id, 'event_actor')
        
        # 从事件历史中获取任务人员相关事件
        events = await event_actor._get_event_history(limit=50, task_id=task_id)
        
        # 模拟返回任务下人员情况
        return {
            'success': True,
            'data': {
                'task_id': task_id,
                'persons': [
                    {
                        'id': 'person_001',
                        'name': '张三',
                        'role': '数据分析师',
                        'status': 'online',
                        'participation': '主要负责人'
                    },
                    {
                        'id': 'person_002',
                        'name': '李四',
                        'role': '软件工程师',
                        'status': 'online',
                        'participation': '技术支持'
                    },
                    {
                        'id': 'person_003',
                        'name': '王五',
                        'role': '项目经理',
                        'status': 'busy',
                        'participation': '项目协调'
                    }
                ]
            },
            'message': '获取任务下人员情况成功'
        }
    
    async def _handle_get_task_leaf_agents(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理获取任务下各个叶子智能体执行情况请求
        
        Args:
            data: 请求数据（通常为空）
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            任务下各个叶子智能体执行情况
        """
        # 获取EventActor服务
        tenant_id = context.get('tenant_id')
        event_actor = await self.tenant_router.get_service(tenant_id, 'event_actor')
        
        # 从事件历史中获取叶子智能体执行情况相关事件
        events = await event_actor._get_event_history(limit=50, task_id=task_id)
        
        # 模拟返回任务下各个叶子智能体执行情况
        return {
            'success': True,
            'data': {
                'task_id': task_id,
                'leaf_agents': [
                    {
                        'id': 'agent_leaf_001',
                        'name': '数据收集子智能体',
                        'status': 'completed',
                        'progress': 100,
                        'result': '数据收集完成，共收集1000条记录'
                    },
                    {
                        'id': 'agent_leaf_002',
                        'name': '数据清洗子智能体',
                        'status': 'running',
                        'progress': 50,
                        'result': '已清洗500条记录'
                    },
                    {
                        'id': 'agent_leaf_003',
                        'name': '数据分析子智能体',
                        'status': 'pending',
                        'progress': 0,
                        'result': ''
                    }
                ]
            },
            'message': '获取任务下各个叶子智能体执行情况成功'
        }
    
    async def _handle_get_task_execution_path(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理获取任务整体执行路径请求
        
        Args:
            data: 请求数据（通常为空）
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            任务整体执行路径
        """
        # 获取EventActor服务
        tenant_id = context.get('tenant_id')
        event_actor = await self.tenant_router.get_service(tenant_id, 'event_actor')
        
        # 从事件历史中获取执行路径相关事件
        events = await event_actor._get_event_history(limit=50, task_id=task_id)
        
        # 模拟返回任务整体执行路径
        return {
            'success': True,
            'data': {
                'task_id': task_id,
                'execution_path': [
                    {
                        'id': 'step_001',
                        'name': '数据收集',
                        'status': 'completed',
                        'start_time': '2023-05-15T10:00:00Z',
                        'end_time': '2023-05-15T10:30:00Z',
                        'agents': ['agent_001', 'agent_leaf_001']
                    },
                    {
                        'id': 'step_002',
                        'name': '数据清洗与预处理',
                        'status': 'running',
                        'start_time': '2023-05-15T10:30:00Z',
                        'agents': ['agent_002', 'agent_leaf_002']
                    },
                    {
                        'id': 'step_003',
                        'name': '模型训练',
                        'status': 'pending',
                        'agents': ['agent_003', 'agent_leaf_003']
                    }
                ]
            },
            'message': '获取任务整体执行路径成功'
        }
    
    async def _handle_get_task_progress(
        self,
        data: Dict[str, Any],
        context: Dict[str, Any],
        task_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        处理获取任务进度详情请求
        
        Args:
            data: 请求数据（通常为空）
            context: 请求上下文
            task_id: 任务ID
            
        Returns:
            任务进度详情
        """
        # 获取EventActor服务
        tenant_id = context.get('tenant_id')
        event_actor = await self.tenant_router.get_service(tenant_id, 'event_actor')
        
        # 从事件历史中获取进度相关事件
        events = await event_actor._get_event_history(limit=50, task_id=task_id)
        
        # 模拟返回任务进度详情
        return {
            'success': True,
            'data': {
                'task_id': task_id,
                'overall_progress': 65,
                'total_steps': 5,
                'completed_steps': 3,
                'running_steps': 1,
                'pending_steps': 1,
                'start_time': '2023-05-15T10:00:00Z',
                'estimated_end_time': '2023-05-15T12:30:00Z',
                'last_updated_time': '2023-05-15T11:30:00Z'
            },
            'message': '获取任务进度详情成功'
        }


# 工厂函数，用于创建请求处理器实例
def create_request_handler(
    tenant_router=None,
    config: Optional[Dict[str, Any]] = None
) -> RequestHandler:
    """
    创建请求处理器实例
    
    Args:
        tenant_router: 租户路由分发器实例
        config: 处理器配置
        
    Returns:
        RequestHandler实例
    """
    return RequestHandler(tenant_router=tenant_router, config=config)
