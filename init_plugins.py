"""
插件初始化入口
负责注册所有能力组件
"""

from capabilities.registry import capability_registry

# 导入需要注册的能力组件
from capabilities.routing.task_router import TaskRouter
from capabilities.routing.task_planner import TaskPlanner
from capabilities.routing.context_resolver import ContextResolver
from capabilities.result_aggregation.result_aggregation import ResultAggregator
from capabilities.parallel.parallel_optimization_interface import ParallelOptimizationInterface
from capabilities.optimization.optimization_interface import OptimizationInterface
from capabilities.llm_memory.memory_capability import MemoryCapability
from capabilities.decision.engine_adapter import DecisionEngine
from capabilities.data_access.data_accessor import DataAccessor
from capabilities.loop_queue.queue_factory import QueueFactory
from capabilities.llm.qwen_adapter import QwenAdapter


def init_plugins():
    """
    初始化所有插件，注册到能力注册表
    """
    print("Initializing plugins...")

    # 1. 注册路由能力
    capability_registry.register_class(
        capability_type="routing",
        capability_class=TaskRouter
    )
    print("✓ Registered routing capability")

    # 2. 注册任务规划能力
    capability_registry.register_class(
        capability_type="planning",
        capability_class=TaskPlanner
    )
    print("✓ Registered planning capability")

    # 3. 注册上下文解析能力
    capability_registry.register_class(
        capability_type="context_resolver",
        capability_class=ContextResolver
    )
    print("✓ Registered context_resolver capability")

    # 4. 注册结果聚合能力
    capability_registry.register_class(
        capability_type="result_aggregation",
        capability_class=ResultAggregator
    )
    print("✓ Registered result_aggregation capability")

    # 5. 注册并行优化能力
    from capabilities.parallel.optuna_optimizer import OptunaOptimizer
    capability_registry.register_class(
        capability_type="parallel_optimization",
        capability_class=OptunaOptimizer
    )
    print("✓ Registered parallel_optimization capability")

    # 6. 注册循环优化能力
    from capabilities.optimization.multi_feature_optimizer import MultiFeatureOptimizer
    capability_registry.register_class(
        capability_type="optimization",
        capability_class=MultiFeatureOptimizer
    )
    print("✓ Registered optimization capability")

    # 7. 注册内存能力
    capability_registry.register_class(
        capability_type="memory",
        capability_class=MemoryCapability
    )
    print("✓ Registered memory capability")

    # 8. 注册决策引擎能力
    capability_registry.register_class(
        capability_type="decision_engine",
        capability_class=DecisionEngine
    )
    print("✓ Registered decision_engine capability")

    # 9. 注册数据访问能力
    capability_registry.register_class(
        capability_type="data_access",
        capability_class=DataAccessor
    )
    print("✓ Registered data_access capability")

    # 10. 注册循环队列能力
    capability_registry.register_class(
        capability_type="loop_queue",
        capability_class=QueueFactory
    )
    print("✓ Registered loop_queue capability")

    # 11. 注册LLM能力
    capability_registry.register_class(
        capability_type="llm",
        capability_class=QwenAdapter
    )
    print("✓ Registered llm capability")

    print("All plugins initialized successfully!")


if __name__ == "__main__":
    init_plugins()
