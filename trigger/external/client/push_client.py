import aiohttp
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PushClient:
    """外部系统客户端"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def ensure_session(self):
        """确保会话存在"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
    
    async def push_task_status(
        self,
        task_id: str,
        status: str,
        scheduled_time: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """推送任务状态到外部系统"""
        try:
            await self.ensure_session()
            
            payload = {
                "task_id": task_id,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            if scheduled_time:
                payload["scheduled_time"] = scheduled_time.isoformat()
            
            async with self.session.post(
                f"{self.base_url}/api/tasks/status",
                json=payload
            ) as response:
                if response.status == 200:
                    logger.debug("Pushed status %s for task %s", status, task_id)
                    return True
                logger.error("Failed to push status: %d", response.status)
                return False
                    
        except Exception as e:
            logger.error("Error pushing status to external system: %s", e)
            return False
    
    async def control_external_task(
        self,
        task_id: str,
        action: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """控制外部系统中的任务"""
        try:
            await self.ensure_session()
            
            payload = {
                "task_id": task_id,
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            async with self.session.post(
                f"{self.base_url}/api/tasks/control",
                json=payload
            ) as response:
                if response.status == 200:
                    logger.debug("Sent %s command for task %s", action, task_id)
                    return True
                logger.error("Failed to send %s command: %d", action, response.status)
                return False
                    
        except Exception as e:
            logger.error("Error controlling external task: %s", e)
            return False
    
    async def close(self):
        """关闭会话"""
        if self.session and not self.session.closed:
            await self.session.close()


async def push_status_to_external(
    task_id: str,
    status: str,
    scheduled_time: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """推送状态到外部系统（单例函数）"""
    # 这里可以配置外部系统的地址
    from config.settings import settings
    
    client = PushClient(
        base_url=settings.EXTERNAL_SYSTEM_URL,
        api_key=settings.EXTERNAL_SYSTEM_API_KEY
    )
    
    try:
        return await client.push_task_status(
            task_id=task_id,
            status=status,
            scheduled_time=scheduled_time,
            metadata=metadata
        )
    finally:
        await client.close()


async def control_external_task(
    task_id: str,
    action: str,
    metadata: Optional[Dict[str, Any]] = None
):
    """控制外部系统中的任务（单例函数）"""
    from config.settings import settings
    
    client = PushClient(
        base_url=settings.EXTERNAL_SYSTEM_URL,
        api_key=settings.EXTERNAL_SYSTEM_API_KEY
    )
    
    try:
        return await client.control_external_task(
            task_id=task_id,
            action=action,
            metadata=metadata
        )
    finally:
        await client.close()
