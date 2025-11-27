# repositories/loop_task_repo.py
from abc import ABC, abstractmethod
from typing import Dict, Optional
from dataclasses import dataclass

@dataclass
class LoopTask:
    task_id: str
    target_actor_address: str  # Thespian 地址转为字符串存储
    message: dict              # JSON-serializable
    interval_sec: int
    next_run_at: float
    is_active: bool = True

class LoopTaskRepository(ABC):
    @abstractmethod
    def save_task(self, task: LoopTask) -> None:
        pass

    @abstractmethod
    def load_task(self, task_id: str) -> Optional[LoopTask]:
        pass

    @abstractmethod
    def delete_task(self, task_id: str) -> bool:
        pass

    @abstractmethod
    def list_active_tasks(self) -> Dict[str, LoopTask]:
        pass

    @abstractmethod
    def update_next_run(self, task_id: str, next_run_at: float) -> bool:
        pass