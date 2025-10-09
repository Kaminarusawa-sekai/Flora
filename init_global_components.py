# init_global_components.py

import importlib
from typing import Type

from config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD, ACTOR_CLASS
from agent.agent_registry import AgentRegistry
from actor_manager.actor_manager import ActorManager
from task_orchestrator.orchestrator import TaskOrchestrator
from agent.agent_actor import AgentActor  # 如果 ACTOR_CLASS 是固定的，可直接导入
from typing import Tuple

def import_class_from_string(class_path: str):
    """动态导入类，例如 'myapp.actors.AgentActor'"""
    module_path, class_name = class_path.rsplit('.', 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


async def init_global_components() -> Tuple[AgentRegistry, ActorManager, TaskOrchestrator]:
    """
    异步初始化所有全局单例组件。
    必须在 async 上下文中调用（如 FastAPI lifespan）。
    """
    # 1. 初始化 AgentRegistry（同步，但线程安全）
    registry = AgentRegistry.get_instance(
        uri=NEO4J_URI,
        user=NEO4J_USER,
        password=NEO4J_PASSWORD
    )

    # 2. 确定 Actor 类
    try:
        actor_cls: Type[AgentActor] = import_class_from_string(ACTOR_CLASS)
    except (ValueError, AttributeError, ImportError):
        actor_cls = AgentActor

    # 3. 初始化 ActorManager（同步）
    actor_manager = ActorManager.get_instance(
        registry=registry,
        actor_class=actor_cls
    )

    # 4. 初始化 TaskOrchestrator（异步！）
    orchestrator = await TaskOrchestrator.get_instance(
        agent_registry=registry
    )

    # 可选：配置参数（同步赋值即可）
    orchestrator.max_task_duration = 300  # 或从 config 读取

    return registry, actor_manager, orchestrator


