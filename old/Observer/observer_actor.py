# observer_actor.py

from thespian.actors import Actor
from messages import TaskEvent
import logging

logger = logging.getLogger(__name__)

class TaskObserver(Actor):
    def __init__(self):
        super().__init__()
        self._active_tasks = {}      # task_id -> dict
        self._task_history = []      # 最近 1000 条完成任务（可替换为 DB）
        self._max_history = 1000

    def receiveMessage(self, msg, sender):
        if isinstance(msg, TaskEvent):
            self._handle_event(msg)
        elif isinstance(msg, dict) and msg.get("query") == "active_tasks":
            self.send(sender, {"active_tasks": self._active_tasks.copy()})
        elif isinstance(msg, dict) and msg.get("query") == "task_history":
            self.send(sender, {"history": self._task_history.copy()})
        else:
            logger.warning(f"Unknown message in Observer: {type(msg)}")

    def _handle_event(self, event: TaskEvent):
        if event.event_type == "started":
            self._active_tasks[event.task_id] = {
                "agent_id": event.agent_id,
                "capability": event.details.get("capability"),
                "start_time": event.timestamp.isoformat(),
                "status": "running",
                "subtasks": [],
                "parent": event.details.get("parent_task_id"),
            }

        elif event.event_type == "subtask_spawned":
            parent_id = event.details.get("parent_task_id")
            if parent_id in self._active_tasks:
                self._active_tasks[parent_id]["subtasks"].append(event.task_id)

        elif event.event_type in ("finished", "failed"):
            if event.task_id in self._active_tasks:
                task_info = self._active_tasks[event.task_id]
                task_info["status"] = event.event_type
                task_info["end_time"] = event.timestamp.isoformat()
                task_info["result"] = event.details.get("result") if event.event_type == "finished" else None
                task_info["error"] = event.details.get("error") if event.event_type == "failed" else None

                # 移入历史（保留最近 N 条）
                if len(self._task_history) >= self._max_history:
                    self._task_history.pop(0)
                self._task_history.append(task_info)

                # 可选：写入 Neo4j（你已有 _neo4j_recorder）
                # self._persist_to_neo4j(event.task_id, task_info)

                del self._active_tasks[event.task_id]