# 直接测试 events 模块，不通过 tasks 包导入
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 直接导入 event_bus 模块
from tasks.events.event_bus import EventBus, event_bus

print("=== 直接测试 event_bus 模块 ===")
print(f"✓ 成功导入 EventBus: {EventBus}")
print(f"✓ 成功导入 event_bus: {event_bus}")
print(f"✓ event_bus 是 EventBus 实例: {isinstance(event_bus, EventBus)}")

# 测试创建新实例
new_bus = EventBus()
print(f"✓ 成功创建 EventBus 实例: {new_bus}")
print(f"✓ 单例模式正常工作: {event_bus is new_bus}")

# 测试 __init__.py 的内容
print("\n=== 测试 __init__.py 内容 ===")
init_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tasks', 'events', '__init__.py')
with open(init_file, 'r', encoding='utf-8') as f:
    init_content = f.read()
    print(init_content)

print("\n=== 测试完成！===")