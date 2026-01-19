from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool
from datetime import datetime, timezone
from typing import AsyncGenerator

# 导入配置
from config.settings import settings

# 创建异步引擎
engine = create_async_engine(
    settings.database_url,
    poolclass=NullPool,  # 使用NullPool避免连接池问题，适合SQLite
    echo=False,  # 生产环境关闭echo
)

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    engine, expire_on_commit=False, class_=AsyncSession
)

# 获取数据库方言
dialect = engine.dialect.name

# 数据库会话依赖
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session

# 自动创建表的函数
async def create_tables():
    """创建所有数据库表"""
    from .models import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
