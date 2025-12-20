from typing import Literal
from sqlalchemy.ext.asyncio import AsyncSession

from ..base import EventInstanceRepository, EventDefinitionRepository
from .sqlite_impl import SQLiteEventInstanceRepository, SQLiteEventDefinitionRepository
from .postgres_impl import PostgreSQLEventInstanceRepository, PostgreSQLEventDefinitionRepository

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