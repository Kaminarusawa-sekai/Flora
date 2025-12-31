from .sqlite_pool import SQLiteConnectionPool
from .dialog_repo import DialogRepository


##TODO:要全部抽象化，允许多种实现
__all__ = [
    "SQLiteConnectionPool",
    "DialogRepository"
]