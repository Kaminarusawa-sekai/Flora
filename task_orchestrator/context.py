# context.py
import contextvars


# ✅ 绑定到 Task（不变）
current_task_id: contextvars.ContextVar[str] = contextvars.ContextVar("task_id")
current_tenant_id: contextvars.ContextVar[str] = contextvars.ContextVar("tenant_id")
current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
current_frame_id: contextvars.ContextVar[str] = contextvars.ContextVar("frame_id")
# ❌ 不再绑定 current_frame_id！
# 因为 Frame 是动态的、嵌套的，而上下文是 Task 级别的。
# 如果需要当前 frame_id，应通过参数显式传递，或从执行栈推导。

# task_context.py
import uuid
from contextlib import contextmanager
from .context import current_task_id, current_tenant_id, current_user_id

@contextmanager
def task_context(*, tenant_id: str, user_id: str, task_id: str = None):
    """
    创建一个 Task 上下文。
    :param tenant_id: 租户 ID
    :param user_id: 用户 ID
    :param task_id: 可选，自定义 task_id；若未提供则自动生成
    """
    if task_id is None:
        task_id = str(uuid.uuid4())

    # 设置上下文
    tokens = {
        "task": current_task_id.set(task_id),
        "tenant": current_tenant_id.set(tenant_id),
        "user": current_user_id.set(user_id),
    }

    try:
        yield task_id
    finally:
        # 恢复上层上下文
        current_task_id.reset(tokens["task"])
        current_tenant_id.reset(tokens["tenant"])
        current_user_id.reset(tokens["user"])