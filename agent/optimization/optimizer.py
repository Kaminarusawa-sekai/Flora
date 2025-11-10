

from typing import Callable, Optional, Dict, Any,Union
from agent.optimization.optimization_task import OptimizationTask
from agent.optimization.optimization_adapter import PersistenceAdapter, EvaluatorAdapter, ImproverAdapter
import logging
from agent.optimization.sqlite_task_persistence import SqlitePersistence
from agent.optimization.llmbase_evaluator import LLMEvaluator
from agent.optimization.inductive_improver import InductiveImprover

logger = logging.getLogger(__name__)



# 兼容旧版：允许传入函数或实现接口的对象
EvaluatorType = Union[EvaluatorAdapter, Callable[[str, Any], float]]
ImproverType = Union[ImproverAdapter, Callable[[str, float], None]]


def _wrap_evaluator(fn: Callable[[str, Any], float]) -> EvaluatorAdapter:
    """将函数包装成 Evaluator 接口"""
    class FuncEvaluator:
        def evaluate(self, task_id: str, result: Any) -> float:
            return fn(task_id, result)
    return FuncEvaluator()


def _wrap_improver(fn: Callable[[str, float], None]) -> ImproverAdapter:
    """将函数包装成 Improver 接口"""
    class FuncImprover:
        def improve(self, task_id: str, score: float) -> None:
            return fn(task_id, score)
    return FuncImprover()


class SelfOptimizer:
    def __init__(
        self,
        owner_agent_id: str,
        executor: Callable[[str, Dict], Any],
        evaluator: Callable[[str, Any], float],
        improver: Callable[[str, float], None],
        recorder: Callable[[str, str, Dict, Any, Optional[float], str], None],
        persistence: Optional[PersistenceAdapter] = None,
    ):
        self.owner_agent_id = owner_agent_id
        self._executor = executor
        # self._evaluator = evaluator
        # self._improver = improver
        self._recorder = recorder
        if not persistence:
            self._persistence =  SqlitePersistence("/thespian_optimizer.db", owner_agent_id)

        if not evaluator:
            evaluator = LLMEvaluator()
        if not improver:
            improver = InductiveImprover(
                kb=kb,
                metrics=metrics,
                all_clauses=all_clauses,
                state_file="/tmp/inductive_state.json"
            )

        self._tasks: Dict[str, OptimizationTask] = {}

          # 统一转为接口对象
        self._global_evaluator = evaluator if isinstance(evaluator, EvaluatorAdapter) else _wrap_evaluator(evaluator)
        self._global_improver = improver if isinstance(improver, ImproverAdapter) else _wrap_improver(improver)

        # 启动时尝试从持久化加载
        if self._persistence:
            try:
                loaded = self._persistence.load_tasks()
                self._tasks.update(loaded)
                logger.info(f"Loaded {len(loaded)} optimization tasks from persistence.")
            except Exception as e:
                logger.error(f"Failed to load tasks from persistence: {e}")

    # --- 任务管理方法（增强：自动持久化） ---
    def add_task(self, task: OptimizationTask):
        self._tasks[task.task_id] = task
        self._save_if_needed()

    def remove_task(self, task_id: str):
        self._tasks.pop(task_id, None)
        self._save_if_needed()

    def pause_task(self, task_id: str):
        if task_id in self._tasks:
            self._tasks[task_id].paused = True
            self._save_if_needed()

    def resume_task(self, task_id: str):
        if task_id in self._tasks:
            self._tasks[task_id].paused = False
            self._save_if_needed()

    def update_task_context(self, task_id: str, new_context: Dict[str, Any]):
        """更新任务上下文（比如调整参数）"""
        if task_id in self._tasks:
            self._tasks[task_id].test_context = new_context
            self._save_if_needed()

    def _save_if_needed(self):
        if self._persistence:
            try:
                self._persistence.save_tasks(self._tasks)
            except Exception as e:
                logger.error(f"Failed to persist tasks: {e}")

    # --- 其他方法保持不变 ---
    def get_next_interval(self, task_id: str) -> Optional[int]:
        task = self._tasks.get(task_id)
        if task and task.enabled and not task.paused:
            return task.interval_seconds
        return None

    def should_run(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        return task is not None and task.enabled and not task.paused

    def run_once(self, task_id: str):
        if not self.should_run(task_id):
            logger.debug(f"Task {task_id} skipped (disabled/paused/removed).")
            return
        self._run_core(task_id)

    def run_once_now(self, task_id: str):
        task = self._tasks.get(task_id)
        if not task or not task.enabled:
            logger.warning(f"Cannot run disabled/missing task {task_id} immediately.")
            return
        self._run_core(task_id, mode="manual")

    def _run_core(self, task_id: str, mode: str = "scheduled"):
        task = self._tasks[task_id]
        try:
            result = self._executor(task.capability, task.test_context)
            # 选择 evaluator：优先任务级，回退全局
            evaluator = task.evaluator or self._global_evaluator
            score = evaluator.evaluate(task_id, result)

            # 选择 improver：优先任务级，回退全局
            improver = task.improver or self._global_improver
            improver.improve(task_id, score)
            ##TODO: 更换统一的recorder
        
            self._recorder(
                agent_id=self.owner_agent_id,
                task_id=task_id,
                params=task.test_context,
                result=result,
                score=score,
                mode=mode
            )
        except Exception as e:
            logger.error(f"Optimization task {task_id} failed (mode={mode}): {e}")


    ##TODO: 历史结果存储待补充
    def _get_previous_result(self, task_id: str) -> Optional[Any]:
        """获取上次执行结果"""
        if task_id in self._task_history and self._task_history[task_id]:
            return self._task_history[task_id][-1]['result']
        return None