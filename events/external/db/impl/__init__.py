from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import EventInstanceRepository, EventDefinitionRepository, EventLogRepository
from .sqlite_impl import SQLiteEventInstanceRepository, SQLiteEventDefinitionRepository, SQLiteEventLogRepository
from .postgres_impl import PostgreSQLEventInstanceRepository, PostgreSQLEventDefinitionRepository, PostgreSQLEventLogRepository

def create_event_instance_repo(
    session: AsyncSession,
    dialect: Literal["sqlite", "postgresql"]
) -> EventInstanceRepository:
    if dialect == "sqlite":
        return SQLiteEventInstanceRepository(session)
    elif dialect == "postgresql":
        return PostgreSQLEventInstanceRepository(session)
    else:
        raise ValueError(f"Unsupported dialect: {dialect}")

def create_event_definition_repo(
    session: AsyncSession,
    dialect: Literal["sqlite", "postgresql"]
) -> EventDefinitionRepository:
    if dialect == "sqlite":
        return SQLiteEventDefinitionRepository(session)
    elif dialect == "postgresql":
        return PostgreSQLEventDefinitionRepository(session)
    else:
        raise ValueError(f"Unsupported dialect: {dialect}")

def create_event_log_repo(
    session: AsyncSession,
    dialect: Literal["sqlite", "postgresql"]
) -> EventLogRepository:
    if dialect == "sqlite":
        return SQLiteEventLogRepository(session)
    elif dialect == "postgresql":
        return PostgreSQLEventLogRepository(session)
    else:
        raise ValueError(f"Unsupported dialect: {dialect}")