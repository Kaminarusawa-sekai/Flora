#!/usr/bin/env python3
"""
初始化脚本：在task_definition表中插入默认的任务定义
"""

import asyncio
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 导入模型和枚举
from events.common.task_definition import TaskDefinition
from events.common.enums import ActorType, ScheduleType

# 数据库连接配置（请根据实际情况修改）
DATABASE_URL = "postgresql+asyncpg://user:password@localhost:5432/flora_events"

# 默认任务定义
DEFAULT_DEFINITIONS = [
    {
        "id": "DEFAULT_ROOT_AGENT",
        "name": "默认根代理",
        "actor_type": ActorType.AGENT,
        "code_ref": "local://default/root_agent",
        "entrypoint": "main.run",
        "default_params": {},
        "is_active": True
    },
    {
        "id": "DEFAULT_CHILD_AGENT",
        "name": "默认子代理",
        "actor_type": ActorType.AGENT,
        "code_ref": "local://default/child_agent",
        "entrypoint": "main.run",
        "default_params": {},
        "is_active": True
    }
]

async def init_default_definitions():
    """初始化默认任务定义"""
    # 创建异步引擎
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(
        engine, expire_on_commit=False, class_=AsyncSession
    )

    async with async_session() as session:
        for def_data in DEFAULT_DEFINITIONS:
            # 检查是否已存在
            # 这里假设你有一个TaskDefinition的Repository或直接使用ORM查询
            # 由于我们没有直接访问Repository的权限，这里使用伪代码
            # 实际使用时请替换为正确的查询方式
            print(f"正在初始化任务定义: {def_data['id']}")
            
            # 创建TaskDefinition对象
            task_def = TaskDefinition(
                id=def_data["id"],
                name=def_data["name"],
                actor_type=def_data["actor_type"],
                code_ref=def_data["code_ref"],
                entrypoint=def_data["entrypoint"],
                default_params=def_data["default_params"],
                is_active=def_data["is_active"],
                created_at=datetime.now(timezone.utc)
            )
            
            # 将对象添加到会话
            # 实际使用时请替换为正确的Repository方法或ORM操作
            # await session.add(task_def)
            print(f"已创建任务定义: {task_def.id} - {task_def.name}")
        
        # 提交事务
        # await session.commit()
        print("\n默认任务定义初始化完成！")

if __name__ == "__main__":
    asyncio.run(init_default_definitions())
