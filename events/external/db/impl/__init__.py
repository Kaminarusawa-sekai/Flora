from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from external.db.base import TaskInstanceRepository
from external.db.impl.sqlite_impl import SQLiteTaskInstanceRepository
from external.db.impl.postgres_impl import PostgreSQLTaskInstanceRepository

def create_task_instance_repo(
    session: AsyncSession,
    dialect: Literal["sqlite", "postgresql"]
) -> TaskInstanceRepository:
    if dialect == "sqlite":
        return SQLiteTaskInstanceRepository(session)
    elif dialect == "postgresql":
        return PostgreSQLTaskInstanceRepository(session)
    else:
        raise ValueError(f"Unsupported dialect: {dialect}")