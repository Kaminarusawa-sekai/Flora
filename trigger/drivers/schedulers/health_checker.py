import asyncio
from datetime import datetime, timedelta, timezone
from typing import List
from ...common.enums import TaskInstanceStatus
from sqlalchemy.ext.asyncio import AsyncSession
from ...config.settings import settings
from ...external.db.impl import create_task_instance_repo
from ...external.db.session import dialect
from sqlalchemy import select
from ...external.db.models import TaskInstanceDB
from sqlalchemy import and_


async def health_checker(async_session_factory):
    """
    健康检查器，定期扫描并处理异常任务
    """
    while True:
        now = datetime.now(timezone.utc)
        
        # 每次循环创建一个新的会话
        async with async_session_factory() as db_session:
            # 初始化任务实例存储库
            inst_repo = create_task_instance_repo(db_session, dialect)
            
            # 1. 检查并处理长时间运行的任务
            timeout_sec = settings.task_timeout_sec
            
            # 获取所有运行中且超过超时时间的任务
            running_tasks = await inst_repo.get_running_instances(timeout_sec)
            
            for task in running_tasks:
                # 将超时任务标记为失败
                await inst_repo.update_status(
                    task.id,
                    "FAILED",
                    error_msg=f"Task timed out after {timeout_sec} seconds"
                )
            
            # 2. 检查并处理长时间处于 PENDING 状态的任务
            pending_timeout_sec = settings.pending_timeout_sec
            pending_threshold = now - timedelta(seconds=pending_timeout_sec)
            
            # 使用SQLAlchemy直接查询
            stmt = select(TaskInstanceDB).where(
                and_(
                    TaskInstanceDB.status == "PENDING",
                    TaskInstanceDB.created_at < pending_threshold
                )
            ).limit(100)
            result = await db_session.execute(stmt)
            pending_tasks = result.scalars().all()
            
            for task in pending_tasks:
                # 告警：长时间处于 PENDING 状态的任务
                print(f"ALERT: Task {task.id} has been PENDING for more than {pending_timeout_sec} seconds")
        
        # 每隔指定秒数执行一次健康检查
        await asyncio.sleep(settings.health_check_interval)
