from typing import Type, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from ..repo import TaskDefinitionRepo, TaskInstanceRepo
from .sqlalchemy_impl import SQLAlchemyTaskDefinitionRepo, SQLAlchemyTaskInstanceRepo

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
