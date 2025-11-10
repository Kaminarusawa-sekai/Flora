# # self_optimizer.py

# import asyncio
# import logging
# from typing import Dict, List, Any, Optional, Callable, Set
# from datetime import datetime

# logger = logging.getLogger(__name__)

# class OptimizationTask:
#     def __init__(
#         self,
#         task_id: str,
#         capability: str,
#         test_context: Dict[str, Any],
#         interval_seconds: int,
#         enabled: bool = True
#     ):
#         self.task_id = task_id
#         self.capability = capability
#         self.test_context = test_context
#         self.interval = interval_seconds
#         self.enabled = enabled
#         self._task: Optional[asyncio.Task] = None

# class SelfOptimizer:
#     def __init__(
#         self,
#         owner_agent_id: str,
#         executor: Callable[[str, Dict], Any],          # (capability, ctx) -> result
#         evaluator: Callable[[str, Any], float],        # (task_id, result) -> score
#         improver: Callable[[str, float], None],        # (task_id, score) -> apply
#         recorder: Callable[[str, str, Dict, Any, Optional[float], str], None],  # 记录函数
#     ):
#         self.owner_agent_id = owner_agent_id
#         self._executor = executor
#         self._evaluator = evaluator
#         self._improver = improver
#         self._recorder = recorder
#         self._tasks: Dict[str, OptimizationTask] = {}
#         self._running: Set[str] = set()

#     def add_task(self, task: OptimizationTask):
#         """添加或更新优化任务"""
#         if task.task_id in self._tasks:
#             self.remove_task(task.task_id)
#         self._tasks[task.task_id] = task
#         if task.enabled:
#             self._start_task(task)

#     def remove_task(self, task_id: str):
#         """停止并移除任务"""
#         if task_id in self._tasks:
#             task = self._tasks[task_id]
#             if task._task and not task._task.done():
#                 task._task.cancel()
#             self._tasks.pop(task_id, None)
#             self._running.discard(task_id)

#     def _start_task(self, task: OptimizationTask):
#         """启动独立的周期性任务"""
#         async def _run_periodically():
#             while True:
#                 try:
#                     if task.task_id not in self._running:
#                         self._running.add(task.task_id)
#                         await self._run_once(task)
#                 except asyncio.CancelledError:
#                     break
#                 except Exception as e:
#                     logger.exception(f"Optimization task {task.task_id} error: {e}")
#                 finally:
#                     self._running.discard(task.task_id)
#                 await asyncio.sleep(task.interval)

#         task._task = asyncio.create_task(_run_periodically())

#     async def _run_once(self, task: OptimizationTask):
#         """执行单次优化流程（非阻塞）"""
#         try:
#             # 1. 执行
#             result = self._executor(task.capability, task.test_context)

#             # 2. 评估
#             score = self._evaluator(task.task_id, result)

#             # 3. 改进
#             self._improver(task.task_id, score)

#             # 4. 记录
#             self._recorder(
#                 agent_id=self.owner_agent_id,
#                 task_id=task.task_id,
#                 params=task.test_context,
#                 result=result,
#                 score=score,
#                 mode="single"
#             )
#         except Exception as e:
#             logger.error(f"Failed to run optimization task {task.task_id}: {e}")
#             raise  # 可选：是否让周期任务继续？

# self_optimizer_aps.py

# import asyncio
# import logging
# from typing import Dict, Any, Optional, Callable
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
# from apscheduler.triggers.interval import IntervalTrigger
# from apscheduler.triggers.cron import CronTrigger

# logger = logging.getLogger(__name__)


# class OptimizationTask:
#     def __init__(
#         self,
#         task_id: str,
#         initial_instruction: str,          # ← 核心：要被优化的指令文本
#         trigger: str = "interval",         # "interval" or "cron"
#         interval_seconds: Optional[int] = None,
#         cron: Optional[str] = None,        # e.g., "0 2 * * *"
#         enabled: bool = True
#     ):
#         self.task_id = task_id
#         self.initial_instruction = initial_instruction
#         self.trigger = trigger
#         self.interval_seconds = interval_seconds
#         self.cron = cron
#         self.enabled = enabled

#         # Validate trigger
#         if trigger == "interval" and interval_seconds is None:
#             raise ValueError("interval_seconds is required for 'interval' trigger")
#         if trigger == "cron" and cron is None:
#             raise ValueError("cron expression is required for 'cron' trigger")


# class SelfOptimizer:
#     def __init__(
#         self,
#         owner_agent_id: str,
#         executor: Callable[[str], Any],
#         evaluator: Callable[[Any], float],
#         improver: Callable[[str, float, Any], str],  # (current_instr, score, result) -> new_instr
#         recorder: Callable[[str, str, str, str, Any, float, str], None],
#         jobstore_url: str = "sqlite:///self_optimizer_jobs.sqlite"
#     ):
#         self.owner_agent_id = owner_agent_id
#         self._executor = executor
#         self._evaluator = evaluator
#         self._improver = improver
#         self._recorder = recorder

#         # Maintain current instruction per task in memory
#         self._current_instructions: Dict[str, str] = {}

#         # APScheduler with persistent job store
#         jobstores = {
#             'default': SQLAlchemyJobStore(url=jobstore_url)
#         }
#         self._scheduler = AsyncIOScheduler(jobstores=jobstores)
#         self._scheduler.start()

#     def add_task(self, task: OptimizationTask):
#         """Add or update a persistent optimization task."""
#         # Build trigger
#         if task.trigger == "interval":
#             trigger = IntervalTrigger(seconds=task.interval_seconds)
#         elif task.trigger == "cron":
#             parts = task.cron.split()
#             if len(parts) != 5:
#                 raise ValueError("Cron must have 5 fields: 'min hour day month dow'")
#             trigger = CronTrigger(
#                 minute=parts[0],
#                 hour=parts[1],
#                 day=parts[2],
#                 month=parts[3],
#                 day_of_week=parts[4]
#             )
#         else:
#             raise ValueError(f"Unsupported trigger: {task.trigger}")

#         # Initialize current instruction from initial_instruction
#         self._current_instructions[task.task_id] = task.initial_instruction

#         # Define the job function
#         def job_func():
#             return asyncio.create_task(self._run_once(task))

#         self._scheduler.add_job(
#             job_func,
#             trigger=trigger,
#             id=task.task_id,
#             replace_existing=True,
#             misfire_grace_time=300,
#             coalesce=True
#         )

#         logger.info(f"Added instruction optimization task: {task.task_id}")

#     def remove_task(self, task_id: str):
#         self._scheduler.remove_job(task_id)
#         self._current_instructions.pop(task_id, None)
#         logger.info(f"Removed task: {task_id}")

#     def pause_task(self, task_id: str):
#         self._scheduler.pause_job(task_id)

#     def resume_task(self, task_id: str):
#         self._scheduler.resume_job(task_id)

#     def shutdown(self):
#         self._scheduler.shutdown(wait=False)

#     async def _run_once(self, task: OptimizationTask):
#         """Execute one instruction optimization cycle."""
#         current_instr = self._current_instructions.get(task.task_id, task.initial_instruction)

#         try:
#             # 1. Execute the current instruction
#             result = self._executor(current_instr)

#             # 2. Evaluate the outcome
#             score = self._evaluator(result)

#             # 3. Improve: generate a new instruction
#             new_instruction = self._improver(current_instr, score, result)

#             # 4. Update internal state
#             self._current_instructions[task.task_id] = new_instruction

#             # 5. Record the full cycle
#             self._recorder(
#                 agent_id=self.owner_agent_id,
#                 task_id=task.task_id,
#                 old_instruction=current_instr,
#                 new_instruction=new_instruction,
#                 result=result,
#                 score=score,
#                 mode=task.trigger
#             )

#             logger.info(f"Task {task.task_id} optimized instruction. Score: {score:.4f}")
#         except Exception as e:
#             logger.exception(f"Optimization cycle failed for {task.task_id}: {e}")


# thespian_self_optimizer.py (支持持久化)

import logging
from typing import Dict, Any, Callable, Optional, Protocol
from dataclasses import dataclass, asdict
import json

from agent.optimization.optimization_adapter import PersistenceAdapter, EvaluatorAdapter, ImproverAdapter

logger = logging.getLogger(__name__)




@dataclass

class OptimizationTask:
    task_id: str
    capability: str
    test_context: Dict[str, Any]
    interval_seconds: int
    enabled: bool = True
    paused: bool = False
    
    # 可选：每个任务自己的 evaluator/improver
    evaluator: Optional[EvaluatorAdapter] = None
    improver: Optional[ImproverAdapter] = None

    def to_dict(self) -> dict:
        # 只保存可持久化的字段
        return {
            "task_id": self.task_id,
            "capability": self.capability,
            "test_context": self.test_context,
            "interval_seconds": self.interval_seconds,
            "enabled": self.enabled,
            "paused": self.paused,
            # 注意：不保存 evaluator / improver
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OptimizationTask":
        # 过滤掉不存在的字段（未来兼容）
        allowed_fields = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in allowed_fields}
        # 移除不可反序列化的字段（如有）
        filtered.pop("evaluator", None)
        filtered.pop("improver", None)
        return cls(**filtered)
