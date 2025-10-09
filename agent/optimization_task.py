# self_optimizer.py

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Set
from datetime import datetime

logger = logging.getLogger(__name__)

class OptimizationTask:
    def __init__(
        self,
        task_id: str,
        capability: str,
        test_context: Dict[str, Any],
        interval_seconds: int,
        enabled: bool = True
    ):
        self.task_id = task_id
        self.capability = capability
        self.test_context = test_context
        self.interval = interval_seconds
        self.enabled = enabled
        self._task: Optional[asyncio.Task] = None

class SelfOptimizer:
    def __init__(
        self,
        owner_agent_id: str,
        executor: Callable[[str, Dict], Any],          # (capability, ctx) -> result
        evaluator: Callable[[str, Any], float],        # (task_id, result) -> score
        improver: Callable[[str, float], None],        # (task_id, score) -> apply
        recorder: Callable[[str, str, Dict, Any, Optional[float], str], None],  # 记录函数
    ):
        self.owner_agent_id = owner_agent_id
        self._executor = executor
        self._evaluator = evaluator
        self._improver = improver
        self._recorder = recorder
        self._tasks: Dict[str, OptimizationTask] = {}
        self._running: Set[str] = set()

    def add_task(self, task: OptimizationTask):
        """添加或更新优化任务"""
        if task.task_id in self._tasks:
            self.remove_task(task.task_id)
        self._tasks[task.task_id] = task
        if task.enabled:
            self._start_task(task)

    def remove_task(self, task_id: str):
        """停止并移除任务"""
        if task_id in self._tasks:
            task = self._tasks[task_id]
            if task._task and not task._task.done():
                task._task.cancel()
            self._tasks.pop(task_id, None)
            self._running.discard(task_id)

    def _start_task(self, task: OptimizationTask):
        """启动独立的周期性任务"""
        async def _run_periodically():
            while True:
                try:
                    if task.task_id not in self._running:
                        self._running.add(task.task_id)
                        await self._run_once(task)
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.exception(f"Optimization task {task.task_id} error: {e}")
                finally:
                    self._running.discard(task.task_id)
                await asyncio.sleep(task.interval)

        task._task = asyncio.create_task(_run_periodically())

    async def _run_once(self, task: OptimizationTask):
        """执行单次优化流程（非阻塞）"""
        try:
            # 1. 执行
            result = self._executor(task.capability, task.test_context)

            # 2. 评估
            score = self._evaluator(task.task_id, result)

            # 3. 改进
            self._improver(task.task_id, score)

            # 4. 记录
            self._recorder(
                agent_id=self.owner_agent_id,
                task_id=task.task_id,
                params=task.test_context,
                result=result,
                score=score,
                mode="single"
            )
        except Exception as e:
            logger.error(f"Failed to run optimization task {task.task_id}: {e}")
            raise  # 可选：是否让周期任务继续？