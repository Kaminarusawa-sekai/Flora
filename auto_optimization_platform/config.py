# config.py
import os
from typing import Dict, Any

class Settings:
    # 优化引擎配置
    DEFAULT_SAMPLER: str = "tpe"  # 可选: "tpe", "cmaes", "random"
    DEFAULT_DIRECTION: str = "maximize"  # 或 "minimize"
    DEFAULT_N_TRIALS: int = 20
    
    # 外部服务地址
    EXECUTOR_BASE_URL: str = "http://executor-service:8000"  # 你的执行器服务
    FEEDBACK_CALLBACK_URL: str = "http://your-platform/callback/feedback"  # 你的反馈接收端点
    
    # 资源管理
    MAX_CONCURRENT_EXECUTIONS: int = 5  # 模拟资源上限，实际应从服务获取
    
    # 其他
    LOG_LEVEL: str = "INFO"

settings = Settings()