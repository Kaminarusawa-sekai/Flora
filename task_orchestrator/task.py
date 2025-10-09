import asyncio
import uuid
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
from task_orchestrator.context import current_task_id, current_frame_id
from task_orchestrator.orchestrator import TaskOrchestrator
from agent.agent_registry import AgentRegistry  
from task_orchestrator.task_frame import TaskFrame


class Task:
    @classmethod
    @asynccontextmanager
    async def context(cls, task_id: str):
        """注意：现在 task_id 必须由 orchestrator 分配，不支持自动生成"""
        token = current_task_id.set(task_id)
        try:
            yield cls()
        finally:
            current_task_id.reset(token)

