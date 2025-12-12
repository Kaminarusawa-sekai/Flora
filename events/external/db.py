import os

# 尝试导入SQLModel，若缺失则提供优雅的错误处理
try:
    from sqlmodel import create_engine, SQLModel, Session
    HAS_SQLMODEL = True
    
    # SQLite 文件路径（可配置）
    DB_PATH = os.getenv("DB_PATH", "command_tower.db")
    DATABASE_URL = f"sqlite:///{DB_PATH}"
    
    # 支持多线程（重要！）
    engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
except ImportError:
    HAS_SQLMODEL = False
    create_engine = None
    SQLModel = None
    Session = None
    engine = None

def init_db():
    """
    初始化数据库，创建所有表
    
    Returns:
        bool: 初始化结果
    """
    if HAS_SQLMODEL and SQLModel and engine:
        SQLModel.metadata.create_all(engine)
        return True
    return False

def get_session():
    """
    获取数据库会话，用于依赖注入
    
    Yields:
        Session: SQLAlchemy会话
    """
    if HAS_SQLMODEL and Session and engine:
        with Session(engine) as session:
            yield session
    else:
        yield None
