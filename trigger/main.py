import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from typing import Any
import sys
import os

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 添加项目根目录到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 导入本地模块
from external.messaging import message_broker
from services.lifecycle_service import LifecycleService
from drivers import health_checker, cron_scheduler
from external.db.session import async_session_factory, create_tables
from entry.api.routes import router, set_lifecycle_service
from config.settings import settings
from services.schedule_scanner import ScheduleScanner
from drivers.schedulers.schedule_dispatcher import ScheduleDispatcher

# 初始化服务实例
broker = message_broker

lifecycle_svc = LifecycleService( broker=broker)

# 将服务实例传递给路由
set_lifecycle_service(lifecycle_svc)

# 创建FastAPI应用
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理，用于启动和关闭后台任务
    """
    
    logger.info("Trigger服务启动中,lifespan上下文管理器...")
    
    # 1. 创建数据库表
    await create_tables()
    
    # 2. 启动后台任务
    tasks = []
    
    # 启动CRON调度器
    tasks.append(asyncio.create_task(cron_scheduler(lifecycle_svc, async_session_factory)))
    
    # 启动任务分发器 (旧版，兼容现有代码)
    from drivers import TaskDispatcher
    dispatcher = TaskDispatcher(broker=broker, lifecycle_service=lifecycle_svc)
    tasks.append(asyncio.create_task(dispatcher.start()))
    
    # 启动新的调度扫描器
    scanner = ScheduleScanner(broker=broker, scan_interval=10)
    tasks.append(asyncio.create_task(scanner.start()))
    
    # 启动新的调度分发器
    schedule_dispatcher = ScheduleDispatcher(broker=broker, lifecycle_service=lifecycle_svc)
    tasks.append(asyncio.create_task(schedule_dispatcher.start()))
    
    # 启动健康检查器
    tasks.append(asyncio.create_task(health_checker(async_session_factory)))
    
    yield
    
    # 3. 清理资源
    # 取消所有后台任务
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    
    logger.info("Trigger服务已停止")

# 创建FastAPI应用实例
app = FastAPI(
    title="Task Orchestration System",
    description="A distributed task scheduling and orchestration system",
    version="1.0.0",
    lifespan=lifespan
)

# 包含API路由
app.include_router(router, prefix="/api/v1")

@app.get("/")
async def root():
    """根路径，返回系统信息"""
    return {
        "name": "Task Orchestration System",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy"
    }


if __name__ == "__main__":
    # 支持两种运行方式：1. 作为FastAPI应用运行 2. 作为独立服务运行
    import uvicorn
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        # 创建一个事件循环并运行lifespan
        async def standalone_main():
            async with lifespan(None):
                logger.info("Trigger服务已启动，按Ctrl+C退出")
                # 保持运行
                await asyncio.Event().wait()
        
        try:
            asyncio.run(standalone_main())
        except KeyboardInterrupt:
            logger.info("Trigger服务已停止")
    else:
        # 作为FastAPI应用运行
        uvicorn.run(
            "__main__:app",
            host="0.0.0.0",
            port=8001,
            reload=True
        )
