class ScheduleConfig(BaseModel):
    """仅用于 recurring 任务"""
    cron: Optional[str] = None  # 如 "0 9 * * 1" 表示每周一9点
    interval_seconds: Optional[int] = None  # 如每3600秒
    next_run: Optional[datetime] = None