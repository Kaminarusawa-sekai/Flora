# optimization/optimizer.py
from datetime import datetime, timezone
from copy import deepcopy
from typing import Dict, Any, Callable

class Optimizer:
    def __init__(self, evaluator: Callable, improver: Callable, neo4j_recorder, execute_fn=None):
        self._evaluator = evaluator
        self._improver = improver
        self._neo4j_recorder = neo4j_recorder
        self._execute_fn = execute_fn  # 用于中间层自调用

    def run_optimization_task(self, agent_id: str, is_leaf: bool, task: Dict, memory=None):
        task_id = task["task_id"]
        capability = task["capability"]
        test_context = task.get("test_context", {})

        try:
            if is_leaf:
                mem_snapshot = deepcopy(memory) if memory is not None else None
                result = self._execute_fn(capability, test_context, mem_snapshot)
            else:
                if self._execute_fn is None:
                    raise NotImplementedError("execute_self_capability_fn not provided")
                result = self._execute_fn(capability, test_context)

            score = self._evaluator(task_id, result)
            self._improver(task_id, score)

            self._neo4j_recorder.record_optimization_trial(
                agent_id=agent_id,
                task_id=task_id,
                params=test_context,
                result=result,
                score=score,
                timestamp=datetime.now(timezone.utc),
                mode="single"
            )
            return result, score
        except Exception as e:
            raise RuntimeError(f"Optimization task {task_id} failed: {e}") from e