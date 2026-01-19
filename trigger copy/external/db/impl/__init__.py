from typing import Type, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from ..repo import TaskDefinitionRepo, TaskInstanceRepo, ScheduledTaskRepo
from .sqlalchemy_impl import SQLAlchemyTaskDefinitionRepo, SQLAlchemyTaskInstanceRepo, SQLAlchemyScheduledTaskRepo

# 数据库方言到仓库类的映射
TASK_DEFINITION_REPO_MAP: Dict[str, Type[TaskDefinitionRepo]] = {
    "sqlite": SQLAlchemyTaskDefinitionRepo,
    "mysql": SQLAlchemyTaskDefinitionRepo,
    "mysql+pymysql": SQLAlchemyTaskDefinitionRepo,
    "postgresql": SQLAlchemyTaskDefinitionRepo,
    "postgresql+asyncpg": SQLAlchemyTaskDefinitionRepo,
}

TASK_INSTANCE_REPO_MAP: Dict[str, Type[TaskInstanceRepo]] = {
    "sqlite": SQLAlchemyTaskInstanceRepo,
    "mysql": SQLAlchemyTaskInstanceRepo,
    "mysql+pymysql": SQLAlchemyTaskInstanceRepo,
    "postgresql": SQLAlchemyTaskInstanceRepo,
    "postgresql+asyncpg": SQLAlchemyTaskInstanceRepo,
}

SCHEDULED_TASK_REPO_MAP: Dict[str, Type[ScheduledTaskRepo]] = {
    "sqlite": SQLAlchemyScheduledTaskRepo,
    "mysql": SQLAlchemyScheduledTaskRepo,
    "mysql+pymysql": SQLAlchemyScheduledTaskRepo,
    "postgresql": SQLAlchemyScheduledTaskRepo,
    "postgresql+asyncpg": SQLAlchemyScheduledTaskRepo,
}


def create_task_definition_repo(session: AsyncSession, dialect: str) -> TaskDefinitionRepo:
    """创建任务定义仓库实例"""
    if dialect not in TASK_DEFINITION_REPO_MAP:
        raise ValueError(f"不支持的数据库方言: {dialect}")
    return TASK_DEFINITION_REPO_MAP[dialect](session)


def create_task_instance_repo(session: AsyncSession, dialect: str) -> TaskInstanceRepo:
    """创建任务实例仓库实例"""
    if dialect not in TASK_INSTANCE_REPO_MAP:
        raise ValueError(f"不支持的数据库方言: {dialect}")
    return TASK_INSTANCE_REPO_MAP[dialect](session)


def create_scheduled_task_repo(session: AsyncSession, dialect: str) -> ScheduledTaskRepo:
    """创建调度任务仓库实例"""
    if dialect not in SCHEDULED_TASK_REPO_MAP:
        raise ValueError(f"不支持的数据库方言: {dialect}")
    return SCHEDULED_TASK_REPO_MAP[dialect](session)
