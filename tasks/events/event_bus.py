""" 
 事件总线实现（轻量级 SDK） 
 - 对外提供同步接口（如 publish_task_event） 
 - 内部通过后台线程 + asyncio loop 异步发送 HTTP 请求 
 - 支持缓冲、重试、解耦 
 - 队列可未来替换为 Redis（只需改 queue 实现） 
 """

from typing import Dict, Any, Optional, List 
import logging 
import httpx 
import uuid 
from datetime import datetime 
import asyncio 
import threading 
import queue 
import time 
from dataclasses import dataclass 
from enum import Enum 

# 导入信号状态枚举 
from common.signal.signal_status import SignalStatus 


class EventType(Enum): 
    TASK_EVENT = "task_event" 
    SPLIT_REQUEST = "split_request" 


@dataclass 
class QueuedEvent: 
    event_type: EventType 
    payload: Dict[str, Any]  # 包含所有必要参数 
    retry_count: int = 0 
    max_retries: int = 3 


class EventPublisher: 
    """ 
    轻量级事件发布 SDK 
    - 同步方法仅入队，非阻塞 
    - 后台线程异步消费并发送 HTTP 请求 
    """

    def __init__( 
        self, 
        lifecycle_base_url: str = "http://localhost:8004", 
        logger: Optional[logging.Logger] = None, 
        max_queue_size: int = 10_000, 
        shutdown_timeout: float = 5.0, 
    ): 
        """初始化事件总线""" 
        self.base_url = lifecycle_base_url.rstrip("/") 
        self.log = logger or logging.getLogger(f"{__name__}.{self.__class__.__name__}") 
        self.shutdown_timeout = shutdown_timeout 

        # 内存队列（未来可替换为 RedisQueue） 
        self._queue: queue.Queue[QueuedEvent] = queue.Queue(maxsize=max_queue_size) 

        # 后台线程和 asyncio loop 
        self._loop: Optional[asyncio.AbstractEventLoop] = None 
        self._thread: Optional[threading.Thread] = None 
        self._running = threading.Event() 
        self._shutdown_complete = threading.Event() 

        # 启动后台消费者线程 
        self._start_background_worker() 

        self.log.info(f"EventPublisher initialized with base URL: {lifecycle_base_url}") 

    def _start_background_worker(self): 
        """启动后台线程运行 asyncio loop""" 
        def run_loop(): 
            self._loop = asyncio.new_event_loop() 
            asyncio.set_event_loop(self._loop) 
            self._running.set() 
            try: 
                self._loop.run_until_complete(self._consume_queue()) 
            finally: 
                self._loop.close() 
                self._shutdown_complete.set() 

        self._thread = threading.Thread(target=run_loop, daemon=True, name="EventPublisherWorker") 
        self._thread.start() 
        self._running.wait()  # 等待 loop 就绪 

    async def _consume_queue(self): 
        """异步消费队列中的事件""" 
        client = httpx.AsyncClient(timeout=10.0) 
        try: 
            while True: 
                try: 
                    # 使用 asyncio 的方式从 queue 中取（需包装） 
                    item = await asyncio.get_event_loop().run_in_executor(None, self._queue.get, True, 1.0) 
                    if item is None:  # 用于触发退出 
                        break 
                except queue.Empty: 
                    continue 

                try: 
                    if item.event_type == EventType.TASK_EVENT: 
                        await self._send_event_request_internal(client, item.payload) 
                    elif item.event_type == EventType.SPLIT_REQUEST: 
                        await self._send_split_request_internal(client, item.payload) 
                    self._queue.task_done() 
                except Exception as e: 
                    self.log.error(f"Failed to process queued event: {e}", exc_info=True) 
                    # 重试机制 
                    if item.retry_count < item.max_retries: 
                        item.retry_count += 1 
                        delay = (2 ** item.retry_count) * 0.5  # 指数退避 
                        await asyncio.sleep(delay) 
                        self._queue.put_nowait(item) 
                    else: 
                        self.log.error(f"Event dropped after {item.max_retries} retries: {item.payload}") 
                        self._queue.task_done() 
        except asyncio.CancelledError: 
            pass 
        finally: 
            await client.aclose() 

    # ======================== 
    # 内部 async 方法（仅供后台使用） 
    # ======================== 

    async def _send_split_request_internal(self, client: httpx.AsyncClient, payload: Dict): 
        """
        专用通道：发送裂变请求
        """
        
        url = f"{self.base_url}/v1/lifecycle/{payload['trace_id']}/split" 
        try: 
            resp = await client.post(url, json=payload["data"]) 
            if resp.status_code >= 400: 
                self.log.error(f"Split task failed: {resp.status_code} - {resp.text}") 
            else: 
                self.log.info(f"Task split successfully: {len(payload['data']['subtasks_meta'])} subtasks created.") 
        except Exception as e: 
            self.log.error(f"Failed to send split request: {str(e)}") 
            raise 

    async def _send_event_request_internal(self, client: httpx.AsyncClient, payload: Dict): 
        """
        通用通道：发送状态事件
        """
        
        url = f"{self.base_url}/v1/lifecycle/events" 
        try: 
            resp = await client.post(url, json=payload) 
            if resp.status_code >= 400: 
                self.log.error(f"Event report failed: {resp.status_code} - {resp.text}") 
            else: 
                self.log.debug(f"Lifecycle event sent: {payload.get('event_type')}") 
        except Exception as e: 
            self.log.error(f"Failed to send event: {str(e)}") 
            raise 

    # ======================== 
    # 同步入口（对外 API） 
    # ======================== 

    def publish_task_event( 
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
        error: Optional[str] = None, 
    ) -> None: 
        """ 
        同步入口：非阻塞地将事件加入队列 
        """ 
        try: 
            safe_data = data or {} 
            
            # 特殊处理 TASK_DISPATCHED → 走 split 路由 
            if event_type == "TASK_DISPATCHED": 
                plans = safe_data.get("plans", []) 
                if plans: 
                    subtasks_meta = [self._adapt_plan_to_meta(p) for p in plans] 
                    snapshot = enriched_context_snapshot or { 
                        "reasoning": safe_data.get("message", ""), 
                        "raw_plans": plans 
                    } 
                    split_payload = { 
                        "trace_id": trace_id, 
                        "parent_id": task_id, 
                        "subtasks_meta": subtasks_meta, 
                        "snapshot": snapshot, 
                    } 
                    event = QueuedEvent( 
                        event_type=EventType.SPLIT_REQUEST, 
                        payload={"trace_id": trace_id, "data": split_payload} 
                    ) 
                    self._enqueue(event) 
                    return 

            # 普通事件 
            safe_data.update({ 
                "task_path": task_path, 
                "message_type": message_type, 
                "user_id": user_id, 
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
                "timestamp": datetime.now().timestamp(), 
            } 
            event = QueuedEvent(event_type=EventType.TASK_EVENT, payload=payload) 
            self._enqueue(event) 

        except Exception as e: 
            self.log.error(f"Failed to enqueue event: {e}", exc_info=True) 

    def _enqueue(self, event: QueuedEvent): 
        """安全入队，丢弃策略：如果队列满则记录警告并丢弃""" 
        try: 
            self._queue.put_nowait(event) 
        except queue.Full: 
            self.log.warning("Event queue is full. Dropping event.") 

    # ======================== 
    # 保留原有 async 接口（供内部或测试使用） 
    # ======================== 

    # async def publish_task_event( 
    #     self, 
    #     task_id: str, 
    #     event_type: str, 
    #     trace_id: str, 
    #     task_path: str, 
    #     source: str, 
    #     agent_id: str, 
    #     data: Optional[Dict[str, Any]] = None, 
    #     user_id: Optional[str] = None, 
    #     message_type: Optional[str] = None, 
    #     enriched_context_snapshot: Optional[Dict[str, Any]] = None, 
    #     error: Optional[str] = None, 
    # ): 
    #     """ 
    #     智能路由的上报方法 
        
    #     Args: 
    #         task_id: 任务ID 
    #         event_type: 事件类型 
    #         trace_id: 用于追踪整个调用链 
    #         task_path: 任务路径 
    #         source: 事件源 
    #         agent_id: 智能体ID 
    #         data: 事件数据 
    #         user_id: 用户ID（可选） 
    #         message_type: 消息类型（可选） 
    #         enriched_context_snapshot: 快照关键上下文（可选） 
    #         error: 错误信息（可选） 
    #     """ 
    #     # 复用同步逻辑生成 payload，但直接 await 发送 
    #     safe_data = data or {} 
    #     if event_type == "TASK_DISPATCHED": 
    #         plans = safe_data.get("plans", []) 
    #         if plans: 
    #             subtasks_meta = [self._adapt_plan_to_meta(p) for p in plans] 
    #             snapshot = enriched_context_snapshot or { 
    #                 "reasoning": safe_data.get("message", ""), 
    #                 "raw_plans": plans 
    #             } 
    #             await self._send_split_request(trace_id, task_id, subtasks_meta, snapshot) 
    #             return 

    #     safe_data.update({ 
    #         "task_path": task_path, 
    #         "message_type": message_type, 
    #         "user_id": user_id, 
    #     }) 
    #     payload = { 
    #         "task_id": task_id, 
    #         "event_type": event_type, 
    #         "trace_id": trace_id, 
    #         "source": source, 
    #         "agent_id": agent_id, 
    #         "data": safe_data, 
    #         "error": error, 
    #         "enriched_context_snapshot": enriched_context_snapshot, 
    #         "timestamp": datetime.now().timestamp(), 
    #     } 
    #     await self._send_event_request(payload) 

    # 原有方法保持兼容 
    # async def publish( 
    #     self, 
    #     trace_id: str, 
    #     event_type: str, 
    #     source: str, 
    #     data: Dict[str, Any], 
    #     level: str = "INFO" 
    # ): 
    #     """ 
    #     全系统通用的埋点方法 (改造为复用 publish_task_event) 
        
    #     Args: 
    #         trace_id: 用于追踪整个调用链 (Task ID) 
    #         event_type: 事件类型 
    #         source: 事件源 
    #         data: 事件数据 
    #         level: 日志级别 
    #     """ 
    #     task_id = data.get('task_id', trace_id) 
    #     agent_id = data.get('agent_id', 'unknown') 
    #     task_path = data.get('task_path', source) 
    #     await self.publish_task_event( 
    #         task_id=task_id, 
    #         event_type=event_type, 
    #         trace_id=trace_id, 
    #         task_path=task_path, 
    #         source=source, 
    #         agent_id=agent_id, 
    #         data=data, 
    #         error=data.get('error'), 
    #         enriched_context_snapshot=data.get('snapshot') 
    #     ) 

    async def get_signal_status(self, trace_id: str) -> Dict[str, Any]: 
        """ 
        获取跟踪链路的当前信号状态 
        
        Args: 
            trace_id: 跟踪链路ID 
            
        Returns: 
            Dict: 包含信号状态的响应数据，其中signal字段为SignalStatus枚举值 
            
        Raises: 
            httpx.RequestError: 如果请求失败 
            httpx.HTTPStatusError: 如果返回非200状态码 
        """ 
        url = f"{self.base_url}/v1/commands/{trace_id}/status" 
        async with httpx.AsyncClient(timeout=10.0) as client: 
            try: 
                resp = await client.get(url) 
                resp.raise_for_status() 
                result = resp.json() 
                signal_value = result.get('signal') 
                if signal_value: 
                    try: 
                        result['signal'] = SignalStatus(signal_value) 
                    except ValueError: 
                        self.log.warning(f"Unknown signal value '{signal_value}' for trace_id {trace_id}, using NORMAL") 
                        result['signal'] = SignalStatus.NORMAL 
                else: 
                    result['signal'] = SignalStatus.NORMAL 
                self.log.info(f"Get signal status successfully for trace_id {trace_id}: {result.get('signal')}") 
                return result 
            except httpx.HTTPStatusError as e: 
                if e.response.status_code == 404: 
                    self.log.warning(f"Signal status not found for trace_id {trace_id}") 
                    raise ValueError(f"Signal status not found for trace_id {trace_id}") from e 
                raise 
            except Exception as e: 
                self.log.error(f"Failed to get signal status: {e}") 
                raise 

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

    # ======================== 
    # 生命周期管理 
    # ======================== 

    def shutdown(self, timeout: Optional[float] = None): 
        """优雅关闭：等待队列处理完毕""" 
        timeout = timeout or self.shutdown_timeout 
        if not self._running.is_set(): 
            return 

        self.log.info("Shutting down EventPublisher...") 
        # 停止生产 
        self._running.clear() 

        # 等待队列处理完毕（最多 timeout 秒） 
        try: 
            self._queue.join() 
        except Exception: 
            pass 

        # 发送退出信号 
        if self._loop and self._thread.is_alive(): 
            asyncio.run_coroutine_threadsafe(self._stop_consume(), self._loop) 

        # 等待线程结束 
        self._shutdown_complete.wait(timeout=timeout) 
        self.log.info("EventPublisher shutdown complete.") 

    async def _stop_consume(self): 
        # 插入 None 作为 poison pill 
        await asyncio.get_event_loop().run_in_executor(None, self._queue.put_nowait, None) 

    def __del__(self): 
        if self._running.is_set(): 
            self.shutdown() 


# 单例实例（注意：在多进程环境中慎用） 
event_bus = EventPublisher()