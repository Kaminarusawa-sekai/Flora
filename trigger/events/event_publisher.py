import httpx
from typing import Dict, Any, Optional
from ..config import settings


class EventPublisher:
    """事件发布器，负责将trace信息发送到events服务"""
    
    def __init__(self):
        self.events_base_url = settings.EVENTS_SERVICE_BASE_URL
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    async def publish_start_trace(self,
                                 root_def_id: str,
                                 trace_id: str,
                                 input_params: Dict[str, Any],
                                 user_id: Optional[str] = None,
                                 initial_context: Optional[Dict[str, Any]] = None):
        """
        发布启动trace事件到events服务
        
        Args:
            root_def_id: 根节点定义ID
            trace_id: 跟踪ID
            input_params: 输入参数
            user_id: 用户ID（可选）
            initial_context: 初始上下文（可选）
        """
        try:
            url = f"{self.events_base_url}/api/v1/traces/start"
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
            print(f"Failed to publish start_trace event: {e}")
            return None
    
    async def close(self):
        """关闭HTTP客户端"""
        await self.http_client.aclose()


# 创建全局事件发布器实例
event_publisher = EventPublisher()
