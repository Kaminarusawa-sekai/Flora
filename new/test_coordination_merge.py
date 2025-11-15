"""测试协调模块与路由模块的合并"""

# 测试导入功能
from new.agents.coordination import (
    TaskCoordinator,
    TaskStatus,
    TaskDependency,
    TaskResult,
    TaskPlanner,
    ContextResolver
)

from new.capabilities.routing import (
    TaskRouter,
    TaskPlanner as RoutingTaskPlanner,
    ContextResolver as RoutingContextResolver,
    TaskStatus as RoutingTaskStatus,
    TaskDependency as RoutingTaskDependency,
    TaskResult as RoutingTaskResult
)

def test_imports():
    """测试所有组件是否能正确导入"""
    print("=== 测试导入功能 ===")
    print(f"TaskCoordinator: {TaskCoordinator}")
    print(f"TaskStatus: {TaskStatus}")
    print(f"TaskDependency: {TaskDependency}")
    print(f"TaskResult: {TaskResult}")
    print(f"TaskPlanner: {TaskPlanner}")
    print(f"ContextResolver: {ContextResolver}")
    print(f"TaskRouter: {TaskRouter}")
    print("所有组件导入成功！")

def test_initialization():
    """测试组件初始化"""
    print("\n=== 测试组件初始化 ===")
    
    # 测试TaskCoordinator
    try:
        coordinator = TaskCoordinator()
        print(f"TaskCoordinator初始化成功: {coordinator}")
    except Exception as e:
        print(f"TaskCoordinator初始化失败: {e}")
    
    # 测试TaskPlanner
    try:
        planner = TaskPlanner()
        print(f"TaskPlanner初始化成功: {planner}")
    except Exception as e:
        print(f"TaskPlanner初始化失败: {e}")
    
    # 测试ContextResolver
    try:
        resolver = ContextResolver()
        print(f"ContextResolver初始化成功: {resolver}")
    except Exception as e:
        print(f"ContextResolver初始化失败: {e}")
    
    # 测试TaskStatus枚举
    try:
        print(f"TaskStatus枚举值: {[status.name for status in TaskStatus]}")
    except Exception as e:
        print(f"TaskStatus测试失败: {e}")

def test_module_equivalence():
    """测试协调模块和路由模块中的组件是否等价"""
    print("\n=== 测试模块等价性 ===")
    
    print(f"TaskPlanner与RoutingTaskPlanner是否相同: {TaskPlanner is RoutingTaskPlanner}")
    print(f"ContextResolver与RoutingContextResolver是否相同: {ContextResolver is RoutingContextResolver}")
    print(f"TaskStatus与RoutingTaskStatus是否相同: {TaskStatus is RoutingTaskStatus}")
    print(f"TaskDependency与RoutingTaskDependency是否相同: {TaskDependency is RoutingTaskDependency}")
    print(f"TaskResult与RoutingTaskResult是否相同: {TaskResult is RoutingTaskResult}")

if __name__ == "__main__":
    test_imports()
    test_initialization()
    test_module_equivalence()
    print("\n=== 所有测试完成！ ===")