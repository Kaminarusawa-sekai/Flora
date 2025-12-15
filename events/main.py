import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager

# 导入 API 路由
from entry.api.v1.commands import router as commands_router
from entry.api.v1.queries import router as queries_router

# 导入依赖初始化
from entry.api.deps import init_services, get_lifecycle_service, get_db_session

# 导入调度器
from drivers.schedulers.cron_generator import cron_scheduler
from drivers.schedulers.dispatcher import TaskDispatcher
from drivers.schedulers.health_checker import health_checker

# 导入外部组件
from external.messaging.rabbitmq_delayed import RabbitMQDelayedMessageBroker
from external.db.sqlalchemy_impl import SQLAlchemyTaskInstanceRepo
from config.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理，用于启动和关闭后台任务
    """
    # 初始化服务
    init_services()
    
    # 获取服务实例
    lifecycle_svc = get_lifecycle_service()
    
    # 获取数据库会话
    db_session = await anext(get_db_session())
    
    # 初始化任务分发器
    broker = RabbitMQDelayedMessageBroker(settings.rabbitmq_url)
    inst_repo = SQLAlchemyTaskInstanceRepo(db_session)
    dispatcher = TaskDispatcher(
        broker=broker,
        inst_repo=inst_repo,
        lifecycle_service=lifecycle_svc,
        worker_url=settings.worker_callback_url
    )
    
    # 启动后台任务
    tasks = []
    
    # 1. 启动 CRON 调度器
    tasks.append(asyncio.create_task(cron_scheduler(lifecycle_svc, db_session)))
    
    # 2. 启动任务分发器
    tasks.append(asyncio.create_task(dispatcher.start()))
    
    # 3. 启动健康检查器
    tasks.append(asyncio.create_task(health_checker(db_session)))
    
    yield
    
    # 关闭后台任务
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


# 创建 FastAPI 应用
app = FastAPI(title="Command Tower", lifespan=lifespan)

# 注册 API 路由
app.include_router(commands_router, prefix="/api/v1")
app.include_router(queries_router, prefix="/api/v1")


@app.get("/")
async def root():
    """
    根路径，返回 API 状态
    """
    return {
        "status": "ok",
        "service": "Command Tower API",
        "version": "v1"
    }


@app.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "healthy",
        "timestamp": "2023-12-15T12:00:00Z"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)