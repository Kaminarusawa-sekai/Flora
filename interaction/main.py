#!/usr/bin/env python3
"""主入口文件"""
import os
import sys
import json

import asyncio
import logging
from contextlib import asynccontextmanager

# 添加 interaction 目录到 Python 路径（优先级最高，确保 interaction/common 优先于根目录的 common/）
INTERACTION_DIR = os.path.dirname(__file__)
sys.path.insert(0, INTERACTION_DIR)

# 添加项目根目录到 Python 路径（用于导入 env）
PROJECT_ROOT = os.path.abspath(os.path.join(INTERACTION_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 从external目录导入API路由
from entry_layer import app as api_app
from entry_layer.api_server import SESSION_QUEUES

# 导入任务结果监听器
from external.message_queue import TaskResultListener
from external.database.dialog_state_repo import DialogStateRepository
from services.task_result_handler import init_task_result_handler

logger = logging.getLogger(__name__)

# 全局变量
_task_result_listener = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global _task_result_listener

    logger.info("Interaction 服务启动中...")

    # 获取 RabbitMQ 配置
    # 从配置文件中读取 rabbitmq 配置
    config_path = os.path.join(INTERACTION_DIR, 'interaction_config.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    rabbitmq_url = config.get('global_config', {}).get('rabbitmq', 'amqp://guest:guest@localhost:5672/')
    task_result_queue = os.getenv('TASK_RESULT_QUEUE', 'work.result')

    # 初始化对话状态仓库
    dialog_repo = DialogStateRepository()

    # 获取当前事件循环
    event_loop = asyncio.get_running_loop()

    # 初始化任务结果处理器
    task_result_handler = init_task_result_handler(
        dialog_repo=dialog_repo,
        session_queues=SESSION_QUEUES,
        event_loop=event_loop
    )

    # 创建并启动任务结果监听器
    _task_result_listener = TaskResultListener(
        rabbitmq_url=rabbitmq_url,
        queue_name=task_result_queue,
        on_result_callback=task_result_handler.handle_task_result
    )
    _task_result_listener.start_in_thread()

    logger.info("Interaction 服务启动完成")

    yield

    # 清理资源
    logger.info("Interaction 服务停止中...")
    if _task_result_listener:
        _task_result_listener.stop()
    logger.info("Interaction 服务已停止")



# 创建主应用
app = FastAPI(
    title="AI任务管理API",
    description="用于管理AI任务的RESTful API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan

)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载API路由
app.mount("/v1", api_app)


if __name__ == "__main__":
    """启动FastAPI服务"""
    uvicorn.run(app, host="0.0.0.0", port=8000)
