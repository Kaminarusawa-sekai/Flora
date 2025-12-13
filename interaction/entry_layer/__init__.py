#!/usr/bin/env python3
"""API路由定义"""

# 从main模块导入主要组件，保持原有API兼容性
from .api_server import app, send_message, resume_task

# 包版本信息（可选）
__version__ = "1.0.0"

# 导出主要组件，方便外部使用
__all__ = [
    "app",
    "send_message",
    "resume_task"
]
