from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from sqlalchemy.orm import sessionmaker
from config.settings import settings
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
        # 1. 创建所有不存在的表
        await conn.run_sync(Base.metadata.create_all)

        # 2. 检查并添加缺失的列（仅支持添加可为空的新列）
        for table_name, table in Base.metadata.tables.items():
            # 查询当前表的列名（使用 PRAGMA）
            result = await conn.execute(text(f"PRAGMA table_info({table_name})"))
            existing_columns = {row[1] for row in result.fetchall()}  # 第2列是 name

            for column_name, column in table.columns.items():
                if column_name not in existing_columns:
                    # 构建 ADD COLUMN 语句
                    col_type = column.type.compile(engine.dialect)
                    nullable = "NULL" if column.nullable else "NOT NULL"
                    
                    # ⚠️ 注意：SQLite 不允许对已有表添加 NOT NULL 列（除非有 DEFAULT）
                    # 所以我们强制设为 NULL，除非有 server_default 或 default
                    if not column.nullable and column.default is None and column.server_default is None:
                        print(f"⚠️ 跳过添加非空列 '{column_name}' 到表 '{table_name}'：缺少默认值，SQLite 不支持。")
                        continue
                    
                    # 如果有 server_default，可以安全设为 NOT NULL
                    if not column.nullable:
                        nullable = "NOT NULL"
                    
                    # 处理默认值
                    default_clause = ""
                    if column.server_default is not None:
                        # server_default 必须是 SQL 表达式（如 text("''")）
                        default_clause = f" DEFAULT {column.server_default.arg}"
                    elif column.default is not None:
                        # Python 默认值无法用于 ALTER，需忽略或提前处理
                        pass  # ALTER 不支持 Python callable 默认值

                    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {col_type} {nullable}{default_clause}"
                    
                    try:
                        await conn.execute(text(alter_sql))
                        print(f"✅ 已添加列: {table_name}.{column_name}")
                    except Exception as e:
                        print(f"❌ 添加列失败: {alter_sql} | 错误: {e}")