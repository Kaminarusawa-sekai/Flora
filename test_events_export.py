# 测试 events 包的导出
from tasks.events import *

# 测试导出的内容
print("测试 events 包导出...")
print(f"EventBus: {EventBus}")
print(f"event_bus: {event_bus}")
print(f"event_bus 类型: {type(event_bus)}")

# 测试创建 EventBus 实例
new_bus = EventBus()
print(f"新创建的 EventBus 实例: {new_bus}")
print(f"单例检查: {event_bus is new_bus}")

print("\n导出测试成功！")