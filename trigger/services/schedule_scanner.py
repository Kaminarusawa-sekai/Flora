import asyncio
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from external.db.impl import create_scheduled_task_repo
from external.db.session import dialect, async_session_factory
from external.messaging.base import MessageBroker

logger = logging.getLogger(__name__)
def get_root_agent_id(definition_id: str) -> str:
    """
    根据 definition_id 获取对应的根节点 agent_id

    Args:
        definition_id: 任务定义ID

    Returns:
        str: 根节点 agent_id
    """
    # TODO: 实现根据 definition_id 查询对应根节点的逻辑
    return "marketing"



class ScheduleScanner:
    """调度扫描器 - 发现需要执行的任务并推送到外部系统"""
    
    def __init__(self, broker: MessageBroker, scan_interval: int = 10):
        self.broker = broker
        self.scan_interval = scan_interval
        self.is_running = False
    
    async def start(self):
        """启动调度扫描器"""
        self.is_running = True
        logger.info("Schedule scanner started")
        
        while self.is_running:
            try:
                await self._scan_pending_tasks()
                await asyncio.sleep(self.scan_interval)
            except Exception as e:
                logger.error(f"Error in schedule scanner: {e}", exc_info=True)
                await asyncio.sleep(60)  # 出错时等待更长时间
    
    async def stop(self):
        """停止调度扫描器"""
        self.is_running = False
        logger.info("Schedule scanner stopped")
    
    async def _scan_pending_tasks(self):
        """扫描待处理任务"""
        async with async_session_factory() as session:
            repo = create_scheduled_task_repo(session, dialect)
            
            # 查找需要执行的任务
            now = datetime.now(timezone.utc)
            pending_tasks = await repo.get_pending_tasks(
                before_time=now,
                limit=100
            )
            
            if pending_tasks:
                logger.info(f"Found {len(pending_tasks)} pending tasks to process")
            
            for task in pending_tasks:
                try:
                    # 更新状态为已调度
                    await repo.update_status(task.id, "SCHEDULED")

                    # 从 input_params 中提取 user_id
                    input_params = task.input_params or {}
                    user_id = input_params.get("_user_id", "system")

                    # 获取根节点 agent_id
                    agent_id = get_root_agent_id(task.definition_id)

                    # 构建执行消息（匹配 tasks 端 callback 期望的格式）
                    execute_msg = {
                        "msg_type": "START_TASK",
                        "task_id": task.trace_id or str(task.id),  # 使用 trace_id 作为任务标识
                        "user_input": input_params.get("description", ""),  # 任务描述作为 user_input
                        "user_id": user_id,
                        "agent_id": agent_id,  # 根节点 agent_id
                        # 附加调度相关信息
                        "schedule_meta": {
                            "definition_id": task.definition_id,
                            "scheduled_time": task.scheduled_time.isoformat(),
                            "round_index": task.round_index,
                            "schedule_config": task.schedule_config,
                            "input_params": input_params
                        }
                    }
                    
                    # 推送到消息队列
                    await self.broker.publish("work.excute", execute_msg)
                    
                    logger.debug(f"Scheduled task {task.id} for execution")
                    
                except Exception as e:
                    logger.error(f"Failed to schedule task {task.id}: {e}")
                    
                    # 记录重试
                    await repo.record_retry(task.id, str(e))
    
    async def scan_and_dispatch_immediate(self):
        """立即扫描并分发任务（用于手动触发）"""
        await self._scan_pending_tasks()
