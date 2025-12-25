import httpx 
import logging 
from typing import Dict, Any, Optional, List 
from datetime import datetime 
from trigger.config import settings

logger = logging.getLogger(__name__)

class EventPublisher: 
    """
    事件发布器 (Client端)
    职责：
    1. 触发器：向 Server 汇报任务状态、变更、等待时间。
    2. 控制请求：向 Server 发送暂停、取消等请求。
    3. 信号接收：向 Server (信号塔) 询问当前 trace 的执行指令。
    """
    
    def __init__(self): 
        # 假设 Server 的 router 挂载在 /api/v1/traces
        self.base_url = settings.EVENTS_SERVICE_BASE_URL.rstrip('/') + "/api/v1/traces"
        self.api_key = settings.EXTERNAL_SYSTEM_API_KEY
        
        self.http_client = httpx.AsyncClient(
            timeout=10.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
    
    async def close(self): 
        await self.http_client.aclose()

    # ----------------------------------------------------------------
    # 1. 触发器功能：启动与状态上报
    # ----------------------------------------------------------------

    async def publish_start_trace(self, 
                                  root_def_id: str, 
                                  trace_id: str, 
                                  input_params: Dict[str, Any], 
                                  user_id: Optional[str] = None,
                                  request_id: Optional[str] = None) -> Optional[Dict]: 
       
        """
        发布启动trace事件到事件系统
        
        Args:
            root_def_id: 根节点定义ID
            trace_id: 跟踪ID
            input_params: 输入参数
            user_id: 用户ID（可选）
            initial_context: 初始上下文（可选）
            request_id: 请求ID（可选）
        """
        """对应 Server: POST /start"""
        if settings.SKIP_EXTERNAL_EVENTS:
            logger.debug("Skipping external event publish (SKIP_EXTERNAL_EVENTS=true)")
            return None
        
        try: 
            url = f"{settings.EVENTS_SERVICE_BASE_URL.rstrip('/')}/api/v1/traces/start"
            payload = {
                "root_def_id": root_def_id,
                "trace_id": trace_id,
                "input_params": input_params
            }
            
            if user_id:
                payload["user_id"] = user_id
            
            if request_id:
                payload["request_id"] = request_id
            
            response = await self.http_client.post(url, json=payload)
            response.raise_for_status()
            
            return response.json()
        except Exception as e: 
            logger.error(f"Failed to start trace: {e}")
            return None

    async def push_task_status(self, 
                               trace_id: str,
                               task_id: str, 
                               status: str, 
                               node_id: Optional[str] = None,
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
        """
        对应 Server: POST /events
        Client 把执行前状态（多久等待、变更）通过 metadata 上报
        """
        if settings.SKIP_EXTERNAL_EVENTS:
            logger.debug("Skipping external event publish (SKIP_EXTERNAL_EVENTS=true)")
            return True
        
        url = f"{settings.EVENTS_SERVICE_BASE_URL.rstrip('/')}/api/v1/traces/events"
        
        # 构造符合 Server ExecutionEventRequest 的结构
        payload = {
            "trace_id": trace_id,
            "task_id": task_id,
            "node_id": node_id, # 如果是具体节点执行
            "event_type": "STATUS_CHANGE",
            "status": status,
            "timestamp": datetime.utcnow().isoformat(),
            "details": metadata or {}  # 包含执行前状态、预计等待时间等
        }
        
        try: 
            response = await self.http_client.post(url, json=payload)
            if response.status_code == 200: 
                return True
            logger.error(f"Failed to push status: {response.status_code} - {response.text}")
            return False
        except Exception as e: 
            logger.error(f"Error pushing status: {e}")
            return False

    

    # ----------------------------------------------------------------
    # 3. 信号塔交互：Client 控制 Server
    # ----------------------------------------------------------------

    async def control_trace(self, trace_id: str, action: str, metadata: Optional[Dict[str, Any]] = None) -> bool: 
        """
        控制整个事件跟踪链路
        
        Args:
            trace_id: 跟踪ID
            action: 操作 (cancel, pause, resume)
            metadata: 元数据（可选）
        
        Returns:
            bool: 是否控制成功
        """
        """
        对应 Server: POST /{trace_id}/cancel | pause | resume
        Client 主动触发全链路控制（例如：检测到致命错误，请求 Server 熔断）
        """
        if settings.SKIP_EXTERNAL_EVENTS:
            logger.debug("Skipping external event publish (SKIP_EXTERNAL_EVENTS=true)")
            return True

        action = action.lower()
        if action not in ['cancel', 'pause', 'resume']:
            logger.error(f"Invalid action: {action}")
            return False
            
        url = f"{settings.EVENTS_SERVICE_BASE_URL.rstrip('/')}/api/v1/traces/{trace_id}/{action}"
        
        try: 
            response = await self.http_client.post(url)
            return response.status_code == 200
        except Exception as e: 
            logger.error(f"Failed to send control {action}: {e}")
            return False
    
    async def control_node(self, trace_id: str, instance_id: str, signal: str, metadata: Optional[Dict[str, Any]] = None) -> bool: 
        """
        级联控制：向指定节点及其子孙发送信号
        
        Args:
            trace_id: 跟踪ID
            instance_id: 节点实例ID
            signal: 信号类型 (CANCEL, PAUSE, RESUME)
            metadata: 元数据（可选）
        
        Returns:
            bool: 是否控制成功
        """
        """
        对应 Server: POST /{trace_id}/nodes/{instance_id}/control
        级联控制：向指定节点及其子孙发送信号 (CANCEL/PAUSE/RESUME)
        """
        if settings.SKIP_EXTERNAL_EVENTS:
            logger.debug("Skipping external event publish (SKIP_EXTERNAL_EVENTS=true)")
            return True

        signal = signal.upper()
        if signal not in ['CANCEL', 'PAUSE', 'RESUME']:
            logger.error(f"Invalid signal: {signal}")
            return False
            
        url = f"{settings.EVENTS_SERVICE_BASE_URL.rstrip('/')}/api/v1/traces/{trace_id}/nodes/{instance_id}/control"
        payload = {
            "signal": signal
        }
        
        if metadata:
            payload["metadata"] = metadata
        
        try: 
            response = await self.http_client.post(url, json=payload)
            return response.status_code == 200
        except Exception as e: 
            logger.error(f"Failed to send node control {signal}: {e}")
            return False
    
    async def control_external_task(self, trace_id: str, action: str, instance_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool: 
        """
        控制事件系统中的任务（统一入口）
        
        Args:
            trace_id: 跟踪ID
            action: 操作 (cancel, pause, resume)
            instance_id: 节点实例ID（可选，为空则控制整个链路）
            metadata: 元数据（可选）
        
        Returns:
            bool: 是否控制成功
        """
        if instance_id:
            # 节点级控制：将 action 映射为 signal
            signal_map = {
                'cancel': 'CANCEL',
                'pause': 'PAUSE',
                'resume': 'RESUME'
            }
            signal = signal_map.get(action.lower())
            if not signal:
                logger.error(f"Invalid action: {action}")
                return False
            return await self.control_node(trace_id, instance_id, signal, metadata)
        else:
            # 链路级控制
            return await self.control_trace(trace_id, action, metadata)

   

    async def get_latest_trace_by_request(self, request_id: str) -> Optional[str]:
        """
        对应 Server: GET /latest-by-request/{request_id}
        根据request_id获取最新的trace_id
        """
        if settings.SKIP_EXTERNAL_EVENTS:
            logger.debug("Skipping external event publish (SKIP_EXTERNAL_EVENTS=true)")
            return None
        
        url = f"{settings.EVENTS_SERVICE_BASE_URL.rstrip('/')}/api/v1/traces/latest-by-request/{request_id}"
        
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()
            result = response.json()
            return result.get("latest_trace_id")
        except Exception as e:
            logger.error(f"Failed to get latest trace by request: {e}")
            return None

   

# 创建全局事件发布器实例
event_publisher = EventPublisher()


async def push_status_to_external(
    task_id: str,
    status: str,
    trace_id: Optional[str] = None,
    node_id: Optional[str] = None,
    scheduled_time: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    推送状态到事件系统（全局函数）
    
    Args:
        task_id: 任务ID
        status: 状态
        trace_id: 跟踪ID
        node_id: 节点ID
        scheduled_time: 计划时间（可选）
        metadata: 元数据（可选）
    
    Returns:
        bool: 是否推送成功
    """
    # 保留 scheduled_time 兼容性，将其添加到 metadata 中
    if scheduled_time and metadata:
        metadata["scheduled_time"] = scheduled_time.isoformat()
    elif scheduled_time:
        metadata = {"scheduled_time": scheduled_time.isoformat()}
    
    return await event_publisher.push_task_status(
        trace_id=trace_id or "",
        task_id=task_id,
        status=status,
        node_id=node_id,
        metadata=metadata
    )


async def control_external_task(
    trace_id: str,
    action: str,
    instance_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    控制事件系统中的任务（全局函数）
    
    Args:
        trace_id: 跟踪ID
        action: 操作 (cancel, pause, resume)
        instance_id: 节点实例ID（可选，为空则控制整个链路）
        metadata: 元数据（可选）
    
    Returns:
        bool: 是否控制成功
    """
    return await event_publisher.control_external_task(
        trace_id=trace_id,
        action=action,
        instance_id=instance_id,
        metadata=metadata
    )
