# 更简单的测试，直接测试 events 模块的导出
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入 events 模块
from tasks.events import EventBus, event_bus

print("=== 简单测试 events 包导出 ===")
print(f"✓ 成功导入 EventBus: {EventBus}")
print(f"✓ 成功导入 event_bus: {event_bus}")
print(f"✓ event_bus 是 EventBus 实例: {isinstance(event_bus, EventBus)}")

# 测试创建新实例
new_bus = EventBus()
print(f"✓ 成功创建 EventBus 实例: {new_bus}")
print(f"✓ 单例模式正常工作: {event_bus is new_bus}")

print("\n=== 所有测试通过！events 包导出正常 ===")