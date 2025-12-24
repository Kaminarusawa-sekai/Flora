import httpx
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from config import settings

logger = logging.getLogger(__name__)


class EventPublisher:
    """事件发布器，负责将trace信息和任务状态发送到事件系统"""
    
    def __init__(self):
        # 统一使用事件系统配置
        self.base_url = settings.EVENTS_SERVICE_BASE_URL.rstrip('/')
        self.api_key = settings.EXTERNAL_SYSTEM_API_KEY
        
        # 统一HTTP客户端配置
        self.http_client = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def publish_start_trace(self,
                                 root_def_id: str,
                                 trace_id: str,
                                 input_params: Dict[str, Any],
                                 user_id: Optional[str] = None,
                                 initial_context: Optional[Dict[str, Any]] = None):
        """
        发布启动trace事件到事件系统
        
        Args:
            root_def_id: 根节点定义ID
            trace_id: 跟踪ID
            input_params: 输入参数
            user_id: 用户ID（可选）
            initial_context: 初始上下文（可选）
        """
        if settings.SKIP_EXTERNAL_EVENTS:
            logger.debug("Skipping external event publish (SKIP_EXTERNAL_EVENTS=true)")
            return None
        
        try:
            url = f"{self.base_url}/api/v1/traces/start"
            payload = {
                "root_def_id": root_def_id,
                "trace_id": trace_id,
                "input_params": input_params
            }
            
            if user_id:
                payload["user_id"] = user_id
            
            if initial_context:
                payload["initial_context"] = initial_context
            
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            
            return response.json()
        except Exception as e:
            # 记录日志，不影响主流程
            logger.error(f"Failed to publish start_trace event: {e}")
            return None
    
    async def push_task_status(self,
                              task_id: str,
                              status: str,
                              scheduled_time: Optional[datetime] = None,
                              metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        推送任务状态到事件系统
        
        Args:
            task_id: 任务ID
            status: 状态
            scheduled_time: 计划时间（可选）
            metadata: 元数据（可选）
        
        Returns:
            bool: 是否推送成功
        """
        if settings.SKIP_EXTERNAL_EVENTS:
            logger.debug("Skipping external event publish (SKIP_EXTERNAL_EVENTS=true)")
            return True
        
        try:
            payload = {
                "task_id": task_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            if scheduled_time:
                payload["scheduled_time"] = scheduled_time.isoformat()
            
            response = await self.http_client.post(
                f"{self.base_url}/api/tasks/status",
                json=payload
            )
            
            if response.status == 200:
                logger.debug("Pushed status %s for task %s", status, task_id)
                return True
            logger.error("Failed to push status: %d", response.status)
            return False
                    
        except Exception as e:
            logger.error("Error pushing status to event system: %s", e)
            return False
    
    async def control_external_task(self,
                                  task_id: str,
                                  action: str,
                                  metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        控制事件系统中的任务
        
        Args:
            task_id: 任务ID
            action: 操作
            metadata: 元数据（可选）
        
        Returns:
            bool: 是否控制成功
        """
        if settings.SKIP_EXTERNAL_EVENTS:
            logger.debug("Skipping external event publish (SKIP_EXTERNAL_EVENTS=true)")
            return True
        
        try:
            payload = {
                "task_id": task_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            response = await self.http_client.post(
                f"{self.base_url}/api/tasks/control",
                json=payload
            )
            
            if response.status == 200:
                logger.debug("Sent %s command for task %s", action, task_id)
                return True
            logger.error("Failed to send %s command: %d", action, response.status)
            return False
                    
        except Exception as e:
            logger.error("Error controlling task in event system: %s", e)
            return False
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()


# 创建全局事件发布器实例
event_publisher = EventPublisher()


async def push_status_to_external(
    task_id: str,
    status: str,
    scheduled_time: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    推送状态到事件系统（全局函数）
    
    Args:
        task_id: 任务ID
        status: 状态
        scheduled_time: 计划时间（可选）
        metadata: 元数据（可选）
    
    Returns:
        bool: 是否推送成功
    """
    return await event_publisher.push_task_status(
        task_id=task_id,
        status=status,
        scheduled_time=scheduled_time,
        metadata=metadata
    )


async def control_external_task(
    task_id: str,
    action: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    控制事件系统中的任务（全局函数）
    
    Args:
        task_id: 任务ID
        action: 操作
        metadata: 元数据（可选）
    
    Returns:
        bool: 是否控制成功
    """
    return await event_publisher.control_external_task(
        task_id=task_id,
        action=action,
        metadata=metadata
    )
