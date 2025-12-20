#!/usr/bin/env python3
"""
测试自动创建表功能
"""
import asyncio
from events.entry.api.deps import create_tables, engine

async def test_create_tables():
    print("开始测试自动创建表...")
    await create_tables()
    print("表创建成功！")
    
    # 检查表是否存在
    async with engine.connect() as conn:
        # 检查task_definitions表
        task_defs_exists = await conn.run_sync(lambda conn: conn.dialect.has_table(conn, "task_definitions"))
        print(f"task_definitions表存在: {task_defs_exists}")
        
        # 检查task_instances表
        task_instances_exists = await conn.run_sync(lambda conn: conn.dialect.has_table(conn, "task_instances"))
        print(f"task_instances表存在: {task_instances_exists}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_create_tables())
