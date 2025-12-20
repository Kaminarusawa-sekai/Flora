from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from ...config.settings import settings
from .models import Base

# 从URL解析数据库类型
def get_dialect_from_url(url: str) -> str:
    if url.startswith("sqlite"):
        return "sqlite"
    elif "postgresql" in url or "postgres://" in url:
        return "postgresql"
    else:
        raise ValueError(f"Unsupported database URL: {url}")

# 获取数据库类型
dialect = get_dialect_from_url(settings.db_url)

# 创建异步引擎
def get_engine_kwargs():
    if dialect == "sqlite":
        return {
            "connect_args": {"check_same_thread": False}
        }
    return {}

database_url = settings.db_url
engine = create_async_engine(database_url, **get_engine_kwargs())

# 创建异步会话工厂
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
    class_=AsyncSession
)

# 全局会话工厂（用于后台任务）
async_session = AsyncSessionFactory

# 依赖函数（用于路由）
async def get_db_session() -> AsyncSession:
    async with AsyncSessionFactory() as session:
        yield session

# 建表函数
async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)