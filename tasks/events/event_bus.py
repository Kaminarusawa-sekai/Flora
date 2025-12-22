"""
事件总线实现
简化为轻量级 SDK，方便系统中的任何地方快速发送事件
"""
from typing import Dict, Any, Optional, List
import logging
import httpx
import uuid
from datetime import datetime


class EventPublisher:
    """
    事件总线实现
    简化为轻量级 SDK，方便系统中的任何地方快速发送事件
    """
    
    def __init__(
        self, 
        lifecycle_base_url: str = "http://localhost:8000",
        logger: Optional[logging.Logger] = None
    ):
        """初始化事件总线"""
        self.base_url = lifecycle_base_url.rstrip("/")
        self.log = logger or logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # 使用持久化 session 连接池，稍微调大超时时间
        self.client = httpx.AsyncClient(timeout=10.0)
        self.log.info(f"EventBus initialized successfully with lifecycle base URL: {lifecycle_base_url}")
    
    async def _send_split_request(self, trace_id: str, parent_id: str, subtasks_meta: List[Dict], snapshot: Dict):
        """
        专用通道：发送裂变请求
        """
        url = f"{self.base_url}/v1/lifecycle/{trace_id}/split"
        payload = {
            "parent_id": parent_id,
            "subtasks_meta": subtasks_meta,
            "reasoning_snapshot": snapshot # 对应 "message" 或其他上下文
        }
        try:
            resp = await self.client.post(url, json=payload)
            if resp.status_code >= 400:
                self.log.error(f"Split task failed: {resp.status_code} - {resp.text}")
            else:
                self.log.info(f"Task split successfully: {len(subtasks_meta)} subtasks created.")
        except Exception as e:
            self.log.error(f"Failed to send split request: {str(e)}")

    async def _send_event_request(self, payload: Dict[str, Any]):
        """
        通用通道：发送状态事件
        """
        url = f"{self.base_url}/v1/lifecycle/events"
        try:
            resp = await self.client.post(url, json=payload)
            if resp.status_code >= 400:
                self.log.error(f"Event report failed: {resp.status_code} - {resp.text}")
            else:
                self.log.debug(f"Lifecycle event sent: {payload.get('event_type')}")
        except Exception as e:
            self.log.error(f"Failed to send event: {str(e)}")

    def _adapt_plan_to_meta(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        【适配器】将 LLM 生成的 Plan 转换为 Lifecycle 需要的 SubtaskMeta
        输入示例:
        {
            "step": 1, "type": "AGENT", "executor": "doc_writer",
            "content": "撰写文档...", "description": "生成文档"
        }
        """
        return {
            # 1. 必须生成一个新的唯一ID
            "id": str(uuid.uuid4()),
            
            # 2. 映射 def_id (关键约定：executor 字段必须对应数据库里的 def_id)
            "def_id": plan.get("executor"),
            
            # 3. 映射名称
            "name": plan.get("description", f"Step {plan.get('step')}"),
            
            # 4. 映射参数 (把 content 放入 params)
            "params": {
                "input_instruction": plan.get("content"),
                "step_index": plan.get("step"),
                "task_type": plan.get("type") # AGENT / MCP
            }
        }
    
    # ----------------------------------------------------------------
    # 兼容旧代码的 publish 方法
    # ----------------------------------------------------------------
    async def publish(
        self, 
        trace_id: str, 
        event_type: str, 
        source: str, 
        data: Dict[str, Any], 
        level: str = "INFO"
    ) -> None:
        """
        全系统通用的埋点方法 (改造为复用 publish_task_event)
        
        Args:
            trace_id: 用于追踪整个调用链 (Task ID)
            event_type: 事件类型
            source: 事件源
            data: 事件数据
            level: 日志级别
        """
        try:
            # 尝试从 data 中提取关键字段，如果提取不到则使用默认值
            task_id = data.get('task_id', trace_id) 
            agent_id = data.get('agent_id', 'unknown')
            task_path = data.get('task_path', source)
            
            # 复用上面的逻辑
            await self.publish_task_event(
                task_id=task_id,
                event_type=event_type,
                trace_id=trace_id,
                task_path=task_path,
                source=source,
                agent_id=agent_id,
                data=data,
                error=data.get('error'), # 尝试自动提取 error
                enriched_context_snapshot=data.get('snapshot') # 尝试自动提取快照
            )
        except Exception as e:
            # 记录日志，但不要影响业务流程
            self.log.error(f"Failed to publish event: {str(e)}", exc_info=True)
    
    async def publish_task_event(
        self, 
        task_id: str, 
        event_type: str, 
        trace_id: str, 
        task_path: str,
        source: str, 
        agent_id: str, 
        data: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        message_type: Optional[str] = None,
        enriched_context_snapshot: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ):
        """
        智能路由的上报方法
        
        Args:
            task_id: 任务ID
            event_type: 事件类型
            trace_id: 用于追踪整个调用链
            task_path: 任务路径
            source: 事件源
            agent_id: 智能体ID
            data: 事件数据
            user_id: 用户ID（可选）
            message_type: 消息类型（可选）
            enriched_context_snapshot: 快照关键上下文（可选）
            error: 错误信息（可选）
        """
        try:
            safe_data = data or {}
            
            # -------------------------------------------------------
            # 路由分支 A: 如果是任务分发 (TASK_DISPATCHED) -> 走 /split
            # -------------------------------------------------------
            if event_type == "TASK_DISPATCHED":
                plans = safe_data.get("plans", [])
                message = safe_data.get("message", "")
                
                if plans:
                    # 1. 数据转换
                    subtasks_meta = [self._adapt_plan_to_meta(p) for p in plans]
                    
                    # 2. 构造快照 (把 message 和原始 plans 记下来作为思维链)
                    snapshot = enriched_context_snapshot or {
                        "reasoning": message,
                        "raw_plans": plans
                    }

                    # 3. 发送裂变请求
                    await self._send_split_request(
                        trace_id=trace_id,
                        parent_id=task_id, # 当前任务即为父任务
                        subtasks_meta=subtasks_meta,
                        snapshot=snapshot
                    )
                    return # 裂变请求处理完直接返回，不需要再报通用事件

            # -------------------------------------------------------
            # 路由分支 B: 普通事件 -> 走 /events
            # -------------------------------------------------------
            safe_data.update({
                "task_path": task_path,
                "message_type": message_type,
                "user_id": user_id
            })

            payload = {
                "task_id": task_id,
                "event_type": event_type,
                "trace_id": trace_id,
                "source": source,
                "agent_id": agent_id,
                "data": safe_data,
                "error": error,
                "enriched_context_snapshot": enriched_context_snapshot,
                "timestamp": datetime.now().timestamp()
            }

            await self._send_event_request(payload)
            
            self.log.info(f"Event published: [{event_type}] {task_id}")

        except Exception as e:
            self.log.error(f"Error in publish_task_event: {str(e)}", exc_info=True)
    


# 创建事件总线单例实例，使用默认的 lifecycle_base_url
event_bus = EventPublisher()
