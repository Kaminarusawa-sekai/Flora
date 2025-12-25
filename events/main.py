import asyncio
from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging

# 导入 API 路由
from entry.api.v1.commands import router as commands_router
from entry.api.v1.queries import router as queries_router

# 导入配置
from config.settings import settings

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理，用于启动和关闭后台任务
    """

    logger.info("应用启动中,lifespan上下文管理器...")
    # 导入依赖
    from entry.api.deps import (
        get_lifecycle_service,
        get_observer_service,
        get_broker,
        get_cache,
        connection_manager_instance
    )
    # 从session.py导入会话相关功能和建表函数
    from external.db.session import async_session, get_db_session, create_tables
    # 导入调度器

    
    # 1. 自动创建数据库表
    await create_tables()
    
    # 2. 初始化默认任务定义（新增部分）
    from common.enums import ActorType, NodeType
    from datetime import datetime, timezone
    from external.db.impl import create_event_definition_repo
    from common.event_definition import EventDefinition
    from external.db.session import dialect
    
    DEFAULT_DEFINITIONS = [
        {
            "id": "DEFAULT_ROOT_AGENT",
            "name": "默认根代理",
            "node_type": NodeType.AGENT_ACTOR,
            "actor_type": ActorType.AGENT,
            "code_ref": "local://default/root_agent",
            "entrypoint": "main.run",
            "default_params": {},
            "is_active": True
        },
        {
            "id": "DEFAULT_CHILD_AGENT",
            "name": "默认子代理",
            "node_type": NodeType.AGENT_ACTOR,
            "actor_type": ActorType.AGENT,
            "code_ref": "local://default/child_agent",
            "entrypoint": "main.run",
            "default_params": {},
            "is_active": True
        }
    ]
    
    session_gen = get_db_session()
    session = await anext(session_gen)
    try:
        repo = create_event_definition_repo(session, dialect)
        for def_data in DEFAULT_DEFINITIONS:
            existing = await repo.get(def_data["id"])
            if not existing:
                event_def = EventDefinition(
                    id=def_data["id"],
                    name=def_data["name"],
                    node_type=def_data["node_type"],
                    actor_type=def_data["actor_type"],
                    code_ref=def_data["code_ref"],
                    entrypoint=def_data["entrypoint"],
                    default_params=def_data["default_params"],
                    is_active=def_data["is_active"],
                    created_at=datetime.now(timezone.utc)
                )
                await repo.create(event_def)
                print(f"✅ 初始化事件定义: {event_def.id}")
        await session.commit()
    except Exception as e:
        await session.rollback()
        print(f"⚠️ 初始化默认事件定义失败: {e}")
    finally:
        await session.close()
    
    # 3. 初始化服务实例
    cache = get_cache()
    broker = get_broker()
    connection_manager = connection_manager_instance
    
    lifecycle_svc = get_lifecycle_service(broker, cache)
    observer_svc = get_observer_service(broker, connection_manager, cache)
    
    # 启动后台任务
    tasks = []
    
    # 启动ObserverService的事件监听任务
    observer_task = asyncio.create_task(
        observer_svc.start_listening()
    )
    tasks.append(observer_task)
    
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
    uvicorn.run("main:app", host=settings.host, port=settings.port, reload=True)