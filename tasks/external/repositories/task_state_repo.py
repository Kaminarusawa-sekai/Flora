"""任务状态存储库 - 用于保存和恢复任务执行状态"""
import json
import logging
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

from external.database.redis_client import RedisClient

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    """任务状态枚举"""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    NEED_INPUT = "NEED_INPUT"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class PausedLayer(str, Enum):
    """任务暂停所在层级"""
    AGENT = "agent"
    TASK_GROUP = "task_group"
    RESULT_AGGREGATOR = "result_aggregator"
    LEAF = "leaf"
    EXECUTION = "execution"


@dataclass
class TaskState:
    """
    任务状态数据结构

    注意：trace_id 是整个链路的唯一标识（前端使用），task_id 是子任务标识
    """
    trace_id: str  # 主键：整个链路的唯一标识
    task_id: str   # 当前子任务 ID
    task_path: str
    status: TaskStatus
    user_id: str

    # 暂停相关
    paused_at: Optional[PausedLayer] = None
    paused_step: Optional[int] = None
    missing_params: Optional[list] = None

    # 执行上下文
    agent_id: Optional[str] = None
    original_content: Optional[str] = None
    original_description: Optional[str] = None
    global_context: Optional[Dict[str, Any]] = None
    enriched_context: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None

    # Leaf 层特有状态
    leaf_state: Optional[Dict[str, Any]] = None

    # 时间戳
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 枚举转字符串
        if isinstance(data.get("status"), TaskStatus):
            data["status"] = data["status"].value
        if isinstance(data.get("paused_at"), PausedLayer):
            data["paused_at"] = data["paused_at"].value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TaskState":
        """从字典创建"""
        # 字符串转枚举
        if "status" in data and isinstance(data["status"], str):
            data["status"] = TaskStatus(data["status"])
        if "paused_at" in data and data["paused_at"] and isinstance(data["paused_at"], str):
            data["paused_at"] = PausedLayer(data["paused_at"])
        return cls(**data)


class TaskStateRepository:
    """
    任务状态存储库

    使用 Redis 存储任务执行状态，支持：
    1. 任务状态的保存和查询（以 trace_id 为主键）
    2. NEED_INPUT 时保存完整上下文
    3. 恢复时加载状态

    注意：所有方法使用 trace_id 作为主键，因为前端只知道 trace_id
    """

    # Redis key 前缀（使用 trace 表明是按 trace_id 索引）
    KEY_PREFIX = "flora:trace:state:"
    # 默认过期时间：24小时
    DEFAULT_TTL = 86400

    def __init__(self, redis_client: Optional[RedisClient] = None):
        """
        初始化任务状态存储库

        Args:
            redis_client: Redis 客户端实例，如果不传则创建新实例
        """
        self._redis = redis_client or RedisClient()
        self._logger = logging.getLogger(__name__)

    def _make_key(self, trace_id: str) -> str:
        """生成 Redis key（使用 trace_id）"""
        return f"{self.KEY_PREFIX}{trace_id}"

    def save_state(self, state: TaskState, ttl: Optional[int] = None) -> bool:
        """
        保存任务状态

        Args:
            state: 任务状态对象
            ttl: 过期时间（秒），默认24小时

        Returns:
            bool: 是否保存成功
        """
        try:
            # 更新时间戳
            now = datetime.now().isoformat()
            if not state.created_at:
                state.created_at = now
            state.updated_at = now

            # 使用 trace_id 作为 key
            key = self._make_key(state.trace_id)
            data = json.dumps(state.to_dict(), ensure_ascii=False, default=str)

            result = self._redis.set(key, data, ttl=ttl or self.DEFAULT_TTL)
            self._logger.info(f"Saved task state: trace_id={state.trace_id}, status={state.status.value}")
            return result
        except Exception as e:
            self._logger.error(f"Failed to save task state trace_id={state.trace_id}: {e}")
            return False

    def get_state(self, trace_id: str) -> Optional[TaskState]:
        """
        获取任务状态

        Args:
            trace_id: 跟踪ID（整个链路的唯一标识）

        Returns:
            TaskState: 任务状态对象，不存在返回 None
        """
        try:
            key = self._make_key(trace_id)
            data = self._redis.get(key)
            if not data:
                return None

            state_dict = json.loads(data)
            return TaskState.from_dict(state_dict)
        except Exception as e:
            self._logger.error(f"Failed to get task state trace_id={trace_id}: {e}")
            return None

    def update_status(self, trace_id: str, status: TaskStatus,
                      extra_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        更新任务状态

        Args:
            trace_id: 跟踪ID
            status: 新状态
            extra_data: 额外要更新的数据

        Returns:
            bool: 是否更新成功
        """
        state = self.get_state(trace_id)
        if not state:
            self._logger.warning(f"Task state not found for update: trace_id={trace_id}")
            return False

        state.status = status
        if extra_data:
            for key, value in extra_data.items():
                if hasattr(state, key):
                    setattr(state, key, value)

        return self.save_state(state)

    def save_need_input_state(
        self,
        trace_id: str,
        task_id: str,
        task_path: str,
        user_id: str,
        paused_at: PausedLayer,
        paused_step: Optional[int],
        missing_params: list,
        agent_id: str,
        original_content: str,
        original_description: str,
        global_context: Dict[str, Any],
        enriched_context: Dict[str, Any],
        parameters: Dict[str, Any],
        leaf_state: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        保存 NEED_INPUT 状态（便捷方法）

        在任务因缺少参数暂停时调用，保存完整的执行上下文

        Args:
            trace_id: 跟踪ID（主键）
            task_id: 当前子任务ID
            其他参数...
        """
        state = TaskState(
            trace_id=trace_id,
            task_id=task_id,
            task_path=task_path,
            status=TaskStatus.NEED_INPUT,
            user_id=user_id,
            paused_at=paused_at,
            paused_step=paused_step,
            missing_params=missing_params,
            agent_id=agent_id,
            original_content=original_content,
            original_description=original_description,
            global_context=global_context,
            enriched_context=enriched_context,
            parameters=parameters,
            leaf_state=leaf_state
        )
        return self.save_state(state)

    def delete_state(self, trace_id: str) -> bool:
        """
        删除任务状态

        Args:
            trace_id: 跟踪ID

        Returns:
            bool: 是否删除成功
        """
        try:
            key = self._make_key(trace_id)
            result = self._redis.delete(key)
            self._logger.info(f"Deleted task state: trace_id={trace_id}")
            return result
        except Exception as e:
            self._logger.error(f"Failed to delete task state trace_id={trace_id}: {e}")
            return False

    def exists(self, trace_id: str) -> bool:
        """
        检查任务状态是否存在

        Args:
            trace_id: 跟踪ID

        Returns:
            bool: 是否存在
        """
        key = self._make_key(trace_id)
        return self._redis.exists(key)


# 单例实例
_task_state_repo: Optional[TaskStateRepository] = None


def get_task_state_repo() -> TaskStateRepository:
    """获取任务状态存储库单例"""
    global _task_state_repo
    if _task_state_repo is None:
        _task_state_repo = TaskStateRepository()
    return _task_state_repo
