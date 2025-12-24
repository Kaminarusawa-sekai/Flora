from croniter import croniter
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import asyncio
import logging
from services.lifecycle_service import LifecycleService
from config.settings import settings
from sqlalchemy.ext.asyncio import AsyncSession
from external.db.impl import create_task_definition_repo
from external.db.session import dialect

logger = logging.getLogger(__name__)

class CronGenerator:
    """
    CRON 表达式生成器，用于生成和解析 CRON 表达式
    """

    @staticmethod
    def is_valid_cron(expr: str) -> bool:
        """
        验证 CRON 表达式是否有效
        """
        parts = expr.strip().split()
        if len(parts) != 5:
            return False
        try:
            croniter(expr)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_next_run_time(expr: str, base_time: Optional[datetime] = None) -> datetime:
        """
        获取 CRON 表达式的下一次执行时间（始终返回 UTC aware datetime）
        """
        if base_time is None:
            base_time = datetime.now(timezone.utc)
        else:
            # 如果 base_time 是 naive，视为 UTC
            if base_time.tzinfo is None:
                base_time = base_time.replace(tzinfo=timezone.utc)
            else:
                # 转为 UTC
                base_time = base_time.astimezone(timezone.utc)

        next_run = croniter(expr, base_time).get_next(datetime)
        
        # croniter 会保持 base_time 的时区属性，但我们再保险一层
        if next_run.tzinfo is None:
            next_run = next_run.replace(tzinfo=timezone.utc)
        
        return next_run

    @staticmethod
    def get_next_n_run_times(expr: str, n: int, base_time: Optional[datetime] = None) -> List[datetime]:
        """
        获取 CRON 表达式的接下来 n 次执行时间
        """
        if not base_time:
            base_time = datetime.now(timezone.utc)
        iter = croniter(expr, base_time)
        return [iter.get_next(datetime) for _ in range(n)]

    @staticmethod
    def generate_simple_cron(interval_minutes: int) -> str:
        """
        生成简单的间隔执行 CRON 表达式
        :param interval_minutes: 执行间隔（分钟）
        :return: CRON 表达式
        """
        if interval_minutes <= 0:
            raise ValueError("interval_minutes must be positive")
        if interval_minutes > 60:
            hours = interval_minutes / 60
            return f"0 */{hours} * * *"
        return f"*/{interval_minutes} * * * *"

    @staticmethod
    def generate_daily_cron(hour: int, minute: int = 0) -> str:
        """
        生成每日执行的 CRON 表达式
        :param hour: 执行小时（0-23）
        :param minute: 执行分钟（0-59）
        :return: CRON 表达式
        """
        return f"{minute} {hour} * * *"

    @staticmethod
    def generate_weekly_cron(day_of_week: int, hour: int = 0, minute: int = 0) -> str:
        """
        生成每周执行的 CRON 表达式
        :param day_of_week: 执行星期几（0-6，0 是周日）
        :param hour: 执行小时（0-23）
        :param minute: 执行分钟（0-59）
        :return: CRON 表达式
        """
        return f"{minute} {hour} * * {day_of_week}"

    @staticmethod
    def generate_monthly_cron(day_of_month: int, hour: int = 0, minute: int = 0) -> str:
        """
        生成每月执行的 CRON 表达式
        :param day_of_month: 执行日期（1-31）
        :param hour: 执行小时（0-23）
        :param minute: 执行分钟（0-59）
        :return: CRON 表达式
        """
        return f"{minute} {hour} {day_of_month} * *"


async def cron_scheduler(lifecycle_svc: LifecycleService, async_session_factory):
    """
    CRON 调度器：每分钟运行一次，精确触发符合时间点的 CRON 任务
    """
    while True:
        now = datetime.now(timezone.utc).replace(second=0, microsecond=0)  # 对齐到整分钟
        
        try:
            # 每次循环创建一个新的会话
            async with async_session_factory() as db_session:
                def_repo = create_task_definition_repo(db_session, dialect)
                cron_defs = await def_repo.list_active_cron()

                for defn in cron_defs:
                    if not defn.cron_expr or not CronGenerator.is_valid_cron(defn.cron_expr):
                        continue

                    try:
                        # 1. 获取完整的任务定义（包含last_triggered_at字段）
                        full_defn = await def_repo.get(defn.id)
                        
                        # 2. 计算下一次应触发时间（基于last_triggered_at或默认值）
                        # 这里需要从数据库直接获取last_triggered_at，目前full_defn是领域模型，不包含该字段
                        # 所以我们直接从数据库查询
                        from external.db.models import TaskDefinitionDB
                        from sqlalchemy import select
                        
                        stmt = select(TaskDefinitionDB.last_triggered_at).where(TaskDefinitionDB.id == defn.id)
                        result = await db_session.execute(stmt)
                        last_triggered_at = result.scalar_one_or_none()
                        
                        base_time = last_triggered_at or (now - timedelta(days=7))
                        next_run = CronGenerator.get_next_run_time(defn.cron_expr, base_time)

                        # 3. 如果当前时间 >= 下次运行时间，则触发
                        if now >= next_run:
                            logger.info(f"Triggering CRON task {defn.id} at {now}, next_run was {next_run}")
                            
                            # 启动新 trace
                            await lifecycle_svc._start_trace_core(
                                session=db_session,
                                def_id=defn.id,
                                input_params={},
                                trigger_type="CRON"
                            )

                            # 4. 更新数据库中的last_triggered_at为本次触发时间（now）
                            await def_repo.update_last_triggered_at(defn.id, now)
                            
                            # 5. 防止同一分钟内重复触发
                            await asyncio.sleep(0.1)

                    except Exception as e:
                        logger.error(f"Error processing CRON definition {defn.id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in cron_scheduler loop: {e}", exc_info=True)

        # Sleep 到下一整分钟
        next_minute = (now + timedelta(minutes=1)).replace(second=0, microsecond=0)
        sleep_sec = (next_minute - datetime.now(timezone.utc)).total_seconds()
        await asyncio.sleep(max(1.0, sleep_sec))