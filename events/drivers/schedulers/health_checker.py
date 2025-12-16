import asyncio
from datetime import datetime, timedelta
from typing import List
from ...external.db.sqlalchemy_impl import SQLAlchemyTaskInstanceRepo
from ...common.enums import TaskInstanceStatus
from sqlalchemy.ext.asyncio import AsyncSession
from ...config.settings import settings


async def health_checker(db_session: AsyncSession):
    """
    健康检查器，定期扫描并处理异常任务
    """
    while True:
        now = datetime.now(timezone.utc)
        
        # 初始化任务实例存储库
        inst_repo = SQLAlchemyTaskInstanceRepo(db_session)
        
        # 1. 检查并处理长时间运行的任务
        # 假设任务超时时间为 300 秒（可配置）
        timeout_sec = 300
        timeout_threshold = now - timedelta(seconds=timeout_sec)
        
        # 获取所有运行中且超过超时时间的任务
        running_tasks = await inst_repo.find_by_trace_id_with_filters(
            trace_id="",  # 空字符串表示所有 trace
            filters={"status": TaskInstanceStatus.RUNNING},
            limit=100
        )
        
        for task in running_tasks:
            if task.started_at and task.started_at < timeout_threshold:
                # 将超时任务标记为失败
                await inst_repo.update_status(
                    task.id,
                    TaskInstanceStatus.FAILED,
                    error_msg=f"Task timed out after {timeout_sec} seconds"
                )
        
        # 2. 检查并处理长时间处于 PENDING 状态的任务
        # 假设 PENDING 超时时间为 3600 秒（1小时）
        pending_timeout_sec = 3600
        pending_threshold = now - timedelta(seconds=pending_timeout_sec)
        
        pending_tasks = await inst_repo.find_by_trace_id_with_filters(
            trace_id="",  # 空字符串表示所有 trace
            filters={"status": TaskInstanceStatus.PENDING},
            limit=100
        )
        
        for task in pending_tasks:
            if task.created_at < pending_threshold:
                # 告警：长时间处于 PENDING 状态的任务
                print(f"ALERT: Task {task.id} has been PENDING for more than {pending_timeout_sec} seconds")
        
        # 每隔 60 秒执行一次健康检查
        await asyncio.sleep(60)
