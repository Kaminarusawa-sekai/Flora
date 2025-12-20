from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import TaskInstanceRepository, TaskDefinitionRepository
from .sqlite_impl import SQLiteTaskInstanceRepository, SQLiteTaskDefinitionRepository
from .postgres_impl import PostgreSQLTaskInstanceRepository, PostgreSQLTaskDefinitionRepository

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

def create_task_definition_repo(
    session: AsyncSession,
    dialect: Literal["sqlite", "postgresql"]
) -> TaskDefinitionRepository:
    if dialect == "sqlite":
        return SQLiteTaskDefinitionRepository(session)
    elif dialect == "postgresql":
        return PostgreSQLTaskDefinitionRepository(session)
    else:
        raise ValueError(f"Unsupported dialect: {dialect}")