"""
直接测试 EventActor 的功能
"""
import time
import uuid
from thespian.actors import ActorSystem
from common.messages.event_message import SystemEventMessage
from external.repositories.event_repo import EventRepository


def test_event_actor():
    """
    直接测试 EventActor 的功能
    """
    print("=== 测试 EventActor ===")
    
    # 生成唯一的 trace_id 用于测试
    trace_id = f"test_actor_{uuid.uuid4()}"
    print(f"测试 trace_id: {trace_id}")
    
    # 初始化 Actor 系统
    system = ActorSystem()
    
    # 创建 EventActor
    event_actor = system.createActor('events.event_actor.EventActor', globalName='TestEventActor')
    print(f"EventActor 地址: {event_actor}")
    
    # 1. 直接向 EventActor 发送事件
    print("\n1. 直接向 EventActor 发送测试事件...")
    
    # 创建并发送任务创建事件
    event1 = SystemEventMessage(
        event_id=str(uuid.uuid4()),
        trace_id=trace_id,
        event_type="TASK_CREATED",
        source_component="TestSource",
        content={"task_name": "测试任务", "priority": "high"},
        timestamp=time.time(),
        level="INFO"
    )
    
    system.tell(event_actor, event1)
    print("发送事件1成功")
    
    # 等待一下，确保事件被处理
    time.sleep(1)
    
    # 创建并发送 Agent 思考事件
    event2 = SystemEventMessage(
        event_id=str(uuid.uuid4()),
        trace_id=trace_id,
        event_type="AGENT_THINKING",
        source_component="test_agent_001",
        content={"thought": "我需要分析这个测试任务"},
        timestamp=time.time(),
        level="INFO"
    )
    
    system.tell(event_actor, event2)
    print("发送事件2成功")
    
    # 等待一下，确保事件被处理
    time.sleep(1)
    
    # 2. 直接查询 EventRepository
    print("\n2. 直接查询 EventRepository...")
    
    # 创建 EventRepository 实例
    event_repo = EventRepository()
    
    # 查询事件时间轴
    timeline = event_repo.get_timeline(trace_id)
    
    # 打印查询结果
    print(f"共查询到 {len(timeline)} 个事件：")
    for i, event in enumerate(timeline):
        print(f"\n{i+1}. 事件类型: {event['event_type']}")
        print(f"   事件源: {event['source']}")
        print(f"   时间: {event['timestamp']}")
        print(f"   内容: {event['content']}")
        print(f"   级别: {event['level']}")
    
    # 3. 验证结果
    print("\n3. 验证结果...")
    
    # 检查是否查询到了所有发送的事件
    expected_event_types = ["TASK_CREATED", "AGENT_THINKING"]
    actual_event_types = [event['event_type'] for event in timeline]
    
    print(f"预期事件类型: {expected_event_types}")
    print(f"实际事件类型: {actual_event_types}")
    
    # 检查是否所有预期事件都存在
    all_events_found = all(event_type in actual_event_types for event_type in expected_event_types)
    
    if all_events_found:
        print("✅ 测试通过：所有预期事件都被成功发送、处理和查询到")
    else:
        print("❌ 测试失败：部分事件未被查询到")
        
        # 找出缺失的事件类型
        missing_events = [event_type for event_type in expected_event_types if event_type not in actual_event_types]
        print(f"缺失的事件类型: {missing_events}")
    
    # 关闭 Actor 系统
    system.shutdown()
    
    print("\n=== 测试完成 ===")
    return all_events_found


if __name__ == "__main__":
    test_event_actor()