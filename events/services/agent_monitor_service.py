import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from external.cache.base import CacheClient
from external.client.agent_client import AgentClient
from external.events.bus import EventBus
from external.db.base import AgentTaskHistoryRepository, AgentDailyMetricRepository

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AgentMonitorService:
    def __init__(self, cache: CacheClient, event_bus: EventBus, 
                 task_history_repo: AgentTaskHistoryRepository,
                 daily_metric_repo: AgentDailyMetricRepository,
                 agent_client: Optional[AgentClient] = None):
        self.cache = cache
        self.event_bus = event_bus
        self.agent_client = agent_client if agent_client is not None else AgentClient()
        # 注入数据库仓库
        self.task_history_repo = task_history_repo
        self.daily_metric_repo = daily_metric_repo
        
        # Key 前缀配置
        self.PREFIX_STATE = "agent:state:"
        self.PREFIX_HISTORY = "agent:history:"
        
        # 配置项
        self.STATE_TTL = 300       # 状态有效期 5分钟
        self.HISTORY_TTL = 86400   # 历史记录保留 24小时 (视业务需求而定)
        self.MAX_HISTORY_LEN = 50  # 看板只展示最近 50 条记录，避免 Redis 大 key
        
        self.topic_name = "job_event_stream"

    def _key_state(self, agent_id: str) -> str:
        return f"{self.PREFIX_STATE}{agent_id}"

    def _key_history(self, agent_id: str) -> str:
        return f"{self.PREFIX_HISTORY}{agent_id}"

    async def update_agent_state(self, agent_id: str, event_type: str, payload: dict):
        """
        统一更新 Agent 状态。
        不仅记录在做什么，还计算'还要做多久'。
        """
        key = self._key_state(agent_id)
        current_time = time.time()
        
        # 1. 获取旧状态 (用于继承一些字段，如开始时间)
        raw_state = await self.cache.get(key)
        old_state = json.loads(raw_state) if raw_state else {}
        
        # 2. 构建新状态基础
        new_state = {
            "last_seen": current_time,
            "agent_id": agent_id,
            "meta": old_state.get("meta", {})
        }

        # 3. 根据事件类型分支处理
        if event_type in ["TASK_STARTED", "STARTED"]:
            # === 刚开始忙 ===
            task_name = payload.get("task_name", "Unknown Task")
            
            # [关键] 异步查询历史平均耗时，用于预估
            avg_duration = await self.task_history_repo.get_avg_duration(task_name)
            
            new_state.update({
                "status": "BUSY",
                "current_task": {
                    "task_id": payload.get("task_id"),
                    "trace_id": payload.get("trace_id"),
                    "name": task_name,
                    "start_time": current_time,
                    "progress": 0,
                    # 预估总耗时 (如果没有历史，默认 60s 或其他逻辑)
                    "estimated_total_duration": avg_duration if avg_duration else 60
                }
            })
            
        elif event_type in ["AGENT_HEARTBEAT", "TASK_PROGRESS"]:
            # === 正在忙 (心跳) ===
            # 如果 Redis 里没有旧状态（比如重启了），我们需要尽量从 payload 恢复
            if not old_state or old_state.get("status") != "BUSY":
                 # 兜底：如果心跳来了但状态是空的，标记为 BUSY 但信息可能不全
                 new_state["status"] = "BUSY"
                 new_state["current_task"] = payload.get("task_info", {})
                 new_state["current_task"]["start_time"] = current_time # 无法追溯，暂用当前
            else:
                # 继承旧任务信息，只更新进度
                current_task = old_state.get("current_task", {})
                
                # 更新进度
                if "task_info" in payload:
                    current_task.update(payload["task_info"]) # 覆盖进度
                
                # [关键] 计算 ETA (剩余时间)
                start_time = current_task.get("start_time", current_time)
                elapsed = current_time - start_time
                total_est = current_task.get("estimated_total_duration", 60)
                
                # 简单的 ETA 逻辑：剩余 = 总预估 - 已过去
                # 也可以根据当前进度推算: (elapsed / progress) * (100 - progress)
                remaining = max(0, total_est - elapsed)
                
                current_task["metrics"] = {
                    "elapsed_seconds": int(elapsed),
                    "estimated_remaining_seconds": int(remaining),
                    "is_overtime": elapsed > total_est # 是否超时
                }
                
                new_state["status"] = "BUSY"
                new_state["current_task"] = current_task

        elif event_type in ["TASK_COMPLETED", "TASK_FAILED"]:
            # === 刚做完 (闲) ===
            # 我们不立即删除 key，而是置为 IDLE，保留最后一次任务的结果供前端展示
            # 前端看到 IDLE，就知道现在没活，但可以看到"刚做完了 Task A"
            new_state.update({
                "status": "IDLE",
                "current_task": None, # 清空当前
                "last_completed_task": {
                    "task_id": payload.get("task_id"),
                    "name": payload.get("task_name"),
                    "finished_at": current_time,
                    "status": "SUCCESS" if event_type == "TASK_COMPLETED" else "FAILED",
                    "result_summary": str(payload.get("result", ""))[:50]
                }
            })

        # 4. 写入 Redis
        await self.cache.set(key, json.dumps(new_state), ex=self.STATE_TTL)
        logger.info(f"Updated state for agent {agent_id}, new status: {new_state['status']}")

    async def report_task_result(self, agent_id: str, task_result: dict):
        """
        [新增] 任务结束上报：用于归档历史
        task_result 结构建议:
        {
            "task_id": "xxx",
            "task_name": "数据清洗",
            "start_time": 1711000000,
            "end_time": 1711000100,
            "duration": 100,
            "status": "SUCCESS" | "FAILED",
            "error_msg": "",
            "trace_id": "xxx"
        }
        """
        logger.info(f"Received task result from agent {agent_id}, task_result: {json.dumps(task_result)}")
        key = self._key_history(agent_id)
        
        # 1. 存入 Redis List (左进)
        await self.cache.lpush(key, json.dumps(task_result))
        
        # 2. 裁剪 List 长度 (保持最近 N 条)，防止无限增长
        await self.cache.ltrim(key, 0, self.MAX_HISTORY_LEN - 1)
        
        # 3. 刷新过期时间 (只要有活动，历史就保留)
        await self.cache.expire(key, self.HISTORY_TTL)
        logger.info(f"Saved task result to history for agent {agent_id}, task_id: {task_result.get('task_id')}")
        
    async def get_agent_backlog(self, agent_id: str) -> List[dict]:
        """
        [新增] 查看这个 Agent 接下来还要做什么。
        这通常需要查询任务队列 (RabbitMQ, Redis List, DB pending tasks)。
        这里需要实现一个接口，然后做一个rabbitmq的实现去查询rabbitmq里的对接任务
        """
        # （无固定 Agent），返回全局 Pool 的排队数
        pending_tasks = await self.task_history_repo.get_pending_tasks_for_agent(agent_id)
        
        # 格式化返回给前端
        return [
            {
                "task_id": t.task_id,
                "name": t.name,
                "trace_id": t.trace_id,
                "priority": t.priority,
                "queued_since": t.created_at.isoformat()
            }
            for t in pending_tasks
        ]

    async def get_agent_history(self, agent_id: str) -> List[dict]:
        """
        [新增] 获取 Agent 的任务历史列表
        """
        key = self._key_history(agent_id)
        # 获取列表所有元素
        raw_list = await self.cache.lrange(key, 0, -1)
        if not raw_list:
            return []
        
        return [json.loads(item) for item in raw_list]

    async def get_agents_status_map(self, agent_ids: List[str]) -> Dict[str, dict]:
        """
        批量获取 Agent 的实时状态 (用于列表页/树状图)
        """
        if not agent_ids:
            return {}
            
        keys = [self._key_state(aid) for aid in agent_ids]
        raw_values = await self.cache.mget(keys)
        
        result = {}
        current_time = time.time()
        
        for agent_id, raw_val in zip(agent_ids, raw_values):
            if not raw_val:
                result[agent_id] = {
                    "is_alive": True,
                    "status_label": "ONLINE",
                    "last_seen_seconds_ago": None,
                    "current_task": None
                }
            else:
                data = json.loads(raw_val)
                last_seen = data.get("last_seen", 0)
                time_diff = current_time - last_seen
                
                # 简单判定：超过 TTL 说明 Redis key 本该消失，这里再做一层逻辑兜底
                status_label = data.get("status", "IDLE")
                if time_diff > self.STATE_TTL:
                    status_label = "ONLINE"

                result[agent_id] = {
                    "is_alive": status_label != "ONLINE",
                    "status_label": status_label,
                    "last_seen_seconds_ago": int(time_diff),
                    "current_task": data.get("current_task")
                }
        return result

    async def enrich_subtree_with_status(self, subtree_root: Dict[str, Any]) -> Dict[str, Any]:
        """
        核心方法：接收静态树，返回带状态的动态树
        """
        # 1. 扁平化收集树中所有的 agent_id
        all_agent_ids = []
        def collect_ids(node):
            if "agent_id" in node:
                all_agent_ids.append(node["agent_id"])
            for child in node.get("children", []):
                collect_ids(child)
        
        collect_ids(subtree_root)
        
        # 2. 批量查询 Redis 状态 (一次网络 IO)
        status_map = await self.get_agents_status_map(all_agent_ids)
        
        # 3. 递归回填状态到树节点中
        def inject_status(node):
            aid = node.get("agent_id")
            if aid in status_map:
                # 将状态注入到节点数据中，建议放在一个新的 runtime 字段下，不污染 meta
                node["runtime_state"] = status_map[aid]
            else:
                # 兜底
                node["runtime_state"] = {"is_alive": False, "status_label": "UNKNOWN"}
            
            # 递归处理子节点
            for child in node.get("children", []):
                inject_status(child)
            return node

        return inject_status(subtree_root)

    async def get_static_agent_tree(self, agent_id: str) -> Dict[str, Any]:
        """
        获取以指定节点为根的静态Agent子树

        Args:
            agent_id: 根节点Agent ID

        Returns:
            静态子树结构，格式如下：
            {
                "agent_id": str,              # 节点Agent ID
                "meta": {                     # 节点元数据
                    "name": str,              # Agent名称
                    "type": str,              # Agent类型
                    "is_leaf": bool,          # 是否为叶子节点
                    "weight": float,          # 权重值
                    "description": str        # 描述信息
                    # 其他元数据字段...
                },
                "children": [                 # 子节点列表（递归结构）
                    {
                        "agent_id": str,
                        "meta": {},
                        "children": [...]
                    }
                    # 更多子节点...
                ]
            }

        Raises:
            requests.exceptions.RequestException: HTTP请求异常
            ValueError: API响应格式错误或请求失败
        """
        # 调用AgentClient的get_agent_subtree方法获取静态树
        return self.agent_client.get_agent_subtree(agent_id)

    async def get_dynamic_agent_tree(self, agent_id: str) -> Dict[str, Any]:
        """
        获取以指定节点为根的动态Agent子树（静态树+运行时状态）

        Args:
            agent_id: 根节点Agent ID

        Returns:
            动态子树结构，格式如下：
            {
                "agent_id": str,              # 节点Agent ID
                "meta": {                     # 节点元数据
                    "name": str,              # Agent名称
                    "type": str,              # Agent类型
                    "is_leaf": bool,          # 是否为叶子节点
                    "weight": float,          # 权重值
                    "description": str        # 描述信息
                    # 其他元数据字段...
                },
                "runtime_state": {           # 运行时状态
                    "is_alive": bool,         # 是否存活
                    "status_label": str,      # 状态标签
                    "last_seen_seconds_ago": int,  # 最后活跃时间
                    "current_task": dict      # 当前任务信息
                },
                "children": [                 # 子节点列表（递归结构）
                    {
                        "agent_id": str,
                        "meta": {},
                        "runtime_state": {},
                        "children": [...]
                    }
                    # 更多子节点...
                ]
            }

        Raises:
            requests.exceptions.RequestException: HTTP请求异常
            ValueError: API响应格式错误或请求失败
        """
        # 1. 获取静态树
        static_tree = await self.get_static_agent_tree(agent_id)
        # 2. 注入运行时状态，返回动态树
        return await self.enrich_subtree_with_status(static_tree)
    
    async def get_agent_dashboard_detail(self, agent_id: str) -> Dict[str, Any]:
        """
        [新增] 核心方法：获取单个工作人员的完整看板数据
        包含：基本信息 + 实时状态 + 任务历史 + 简单统计
        """
        # 1. 获取静态信息 (如果agent_client支持)
        static_info = {}
        try:
            static_info = await self.agent_client.get_agent_metadata(agent_id) or {}
        except Exception:
            # 容错处理，如果agent_client不支持get_agent_metadata方法
            pass
        
        # 2. 实时状态 (Redis)
        status_map = await self.get_agents_status_map([agent_id])
        current_state = status_map.get(agent_id, {})
        
        # 3. 历史履历 (Database) - 相比Redis List，用DB我们可以做分页、按时间筛选
        history_list = await self.task_history_repo.get_recent_tasks(agent_id, limit=50)
        
        # 4. 绩效统计 (从数据库获取更准确的统计数据)
        statistics = await self.task_history_repo.get_task_statistics(agent_id)
        total_tasks = statistics.get('total_tasks', 0)
        success_tasks = statistics.get('success_tasks', 0)
        success_rate = (success_tasks / total_tasks * 100) if total_tasks > 0 else 0
        avg_duration = statistics.get('avg_duration_ms', 0) / 1000  # 转换为秒
        
        # 5. 最近7天的趋势数据 (可选)
        recent_metrics = await self.daily_metric_repo.get_recent_metrics(agent_id, days=7)
        
        # 6. 获取实时状态数据（用于获取更详细的任务信息和ETA）
        key = self._key_state(agent_id)
        raw_state = await self.cache.get(key)
        state_data = json.loads(raw_state) if raw_state else None
        
        # 7. 判断真实状态
        status_label = "OFFLINE"
        current_task_display = None
        metrics_display = None
        
        if state_data:
            status_label = state_data.get("status", "IDLE")
            current_task = state_data.get("current_task")
            if status_label == "BUSY" and current_task:
                current_task_display = {
                    "name": current_task.get("name"),
                    "trace_id": current_task.get("trace_id"),
                    "progress": current_task.get("progress", 0)
                }
                metrics_display = current_task.get("metrics") # 包含 ETA
        
        # 8. 获取积压任务 (Next Steps)
        backlog = await self.get_agent_backlog(agent_id)

        # 9. 组装看板数据结构
        return {
            "agent_id": agent_id,
            # 卡片头部：身份信息
            "profile": {
                "name": static_info.get("name", "Unknown Agent"),
                "role": static_info.get("type", "Worker"),
                "avatar": static_info.get("avatar", "")
            },
            # 卡片状态栏：红绿灯
            "runtime": {
                "is_online": current_state.get("is_alive", False),
                "status": status_label, # BUSY, IDLE, OFFLINE
                "last_active": f"{current_state.get('last_seen_seconds_ago')} seconds ago",
                "current_focus": current_task_display, # 正在干的活
                "timing": metrics_display, # 前端据此显示倒计时
                "last_completed_task": state_data.get("last_completed_task") if state_data else None # 最近完成的任务
            },
            # 卡片统计区：绩效
            "metrics": {
                "total_tasks": total_tasks,
                "success_rate": f"{success_rate:.1f}%",
                "avg_duration": f"{avg_duration:.2f}s",
                "success_tasks": success_tasks,
                "failed_tasks": statistics.get('failed_tasks', 0)
            },
            # 卡片趋势区：最近7天走势
            "trend": recent_metrics,
            # 卡片列表区：流水账
            "recent_history": history_list, # 前端可以直接渲染 timeline
            # 卡片待处理任务区：接下来要做什么
            "next_up": {
                "count": len(backlog),
                "preview": backlog[:3] # 只展示前3个
            }
        }
    
    async def handle_task_completed_event(self, payload: Dict[str, Any]):
        """
        处理任务完成/失败事件
        这是一个"归档"动作：
        1. 清理/更新 Redis 里的当前状态
        2. 将完整记录写入 Database
        """
        agent_id = payload.get("agent_id")
        if not agent_id:
            logger.warning(f"Task completed event received without agent_id, payload: {json.dumps(payload)}")
            return
        
        task_id = payload.get("task_id")
        status = payload.get("status")
        logger.info(f"Handling task completed event for agent {agent_id}, task_id: {task_id}, status: {status}")

        # 1. 更新 Redis 状态 (可选：也可以等下一次心跳覆盖，但主动更新更实时)
        # 任务结束了，Agent 理论上变回 IDLE，或者保留 Last Result
        key = self._key_state(agent_id)
        # 我们不仅要把它变闲，最好把上一个任务的结果稍微缓存一下，方便前端弹窗"刚刚完成了啥"
        raw_state = await self.cache.get(key)
        if raw_state:
            state = json.loads(raw_state)
            state["status"] = "IDLE"
            state["last_completed_task"] = payload # 暂存一下最后的结果
            # 清空 current_task
            state["current_task"] = None
            await self.cache.set(key, json.dumps(state), ex=self.STATE_TTL)
            logger.info(f"Updated agent {agent_id} state to IDLE after task completion")
        else:
            logger.info(f"No existing state found for agent {agent_id} when handling task completion")

        # 2. 写入 Redis 历史列表 (用于快速查询最近记录)
        await self.report_task_result(agent_id, payload)

        # 3. 写入数据库 (持久化)
        await self.task_history_repo.create(payload)
        logger.info(f"Saved task {task_id} result to database for agent {agent_id}")

        # 4. 更新日结统计表 (可选，但推荐)
        end_time = payload.get("end_time")
        if end_time:
            if isinstance(end_time, str):
                end_date = datetime.fromisoformat(end_time).date()
            elif isinstance(end_time, datetime):
                end_date = end_time.date()
            else:
                end_date = datetime.now().date()
            
            duration_ms = payload.get("duration_ms")
            if duration_ms is None:
                # 尝试计算持续时间
                start_time = payload.get("start_time")
                if start_time and isinstance(start_time, (str, datetime)):
                    if isinstance(start_time, str):
                        start_time = datetime.fromisoformat(start_time)
                    if isinstance(end_time, str):
                        end_time = datetime.fromisoformat(end_time)
                    duration_ms = int((end_time - start_time).total_seconds() * 1000)
                else:
                    duration_ms = 0
            
            await self.daily_metric_repo.update_daily_metric(
                agent_id=agent_id,
                date_str=end_date.isoformat(),
                status=payload.get("status", "COMPLETED"),
                duration_ms=duration_ms
            )
            logger.info(f"Updated daily metrics for agent {agent_id} on {end_date.isoformat()}")

    async def handle_event(self, message: Dict[str, Any]):
        """
        事件监听路由增强
        """
        event_type = message.get("event_type")
        payload = message.get("payload", {})
        agent_id = payload.get("agent_id")
        logger.info(f"Received event: {event_type}, agent_id: {agent_id}, payload: {json.dumps(payload)}")

        if not agent_id:
            logger.warning(f"Event {event_type} received without agent_id, payload: {json.dumps(payload)}")
            return

        # 统一路由到状态更新逻辑
        if event_type in ["TASK_STARTED", "TASK_COMPLETED", "TASK_FAILED", "AGENT_HEARTBEAT", "TASK_PROGRESS"]:
             await self.update_agent_state(agent_id, event_type, payload)
        
        # 只有完成事件才归档历史
        if event_type in ["TASK_COMPLETED", "TASK_FAILED"]:
            # 确保payload包含status字段
            if event_type == "TASK_COMPLETED":
                payload["status"] = "COMPLETED"
            else:
                payload["status"] = "FAILED"
            # 处理任务完成/失败事件
            await self.handle_task_completed_event(payload)
        else:
            logger.info(f"Event {event_type} for agent {agent_id} not handled")
    
    async def start_listening(self):
        """
        启动事件监听
        """
        logger.info(f"Starting event listener for topic: {self.topic_name}")
        try:
            async for message in self.event_bus.subscribe(self.topic_name):
                try:
                    await self.handle_event(message)
                except Exception as e:
                    logger.error(f"Error handling event: {e}, message: {json.dumps(message)}", exc_info=True)
        except Exception as e:
            logger.critical(f"Event listener failed with exception: {e}", exc_info=True)
        finally:
            logger.info(f"Event listener stopped for topic: {self.topic_name}")
