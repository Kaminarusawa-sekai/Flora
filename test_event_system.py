"""
测试重构后的 Event 系统
"""
import time
import uuid
from events.event_bus import event_bus
from external.repositories.event_repo import EventRepository


def test_event_system():
    """
    测试事件系统的完整流程：发布 -> 持久化 -> 查询
    """
    print("=== 测试 Event 系统 ===")
    
    # 生成唯一的 trace_id 用于测试
    trace_id = f"test_{uuid.uuid4()}"
    print(f"测试 trace_id: {trace_id}")
    
    # 1. 发布事件
    print("\n1. 发布测试事件...")
    
    # 发布任务创建事件
    event_bus.publish(
        trace_id=trace_id,
        event_type="TASK_CREATED",
        source="TestSource",
        data={"task_name": "测试任务", "priority": "high"}
    )
    
    # 等待一下，确保事件被处理
    time.sleep(1)
    
    # 发布 Agent 思考事件
    event_bus.publish_agent_thinking(
        trace_id=trace_id,
        agent_id="test_agent_001",
        thought="我需要分析这个测试任务"
    )
    
    # 等待一下，确保事件被处理
    time.sleep(1)
    
    # 发布工具调用事件
    event_bus.publish_tool_event(
        trace_id=trace_id,
        tool_name="TestTool",
        params={"param1": "value1", "param2": "value2"},
        result={"status": "success", "data": "test_result"}
    )
    
    # 等待一下，确保事件被处理
    time.sleep(1)
    
    # 发布任务完成事件
    event_bus.publish(
        trace_id=trace_id,
        event_type="TASK_COMPLETED",
        source="TestSource",
        data={"result": "测试任务完成", "duration": 5.5}
    )
    
    # 等待一下，确保事件被处理
    time.sleep(2)
    
    # 2. 查询事件
    print("\n2. 查询事件时间轴...")
    
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
    
    # 检查是否查询到了所有发布的事件
    expected_event_types = ["TASK_CREATED", "AGENT_THINKING", "TOOL_CALLED", "TOOL_RESULT", "TASK_COMPLETED"]
    actual_event_types = [event['event_type'] for event in timeline]
    
    print(f"预期事件类型: {expected_event_types}")
    print(f"实际事件类型: {actual_event_types}")
    
    # 检查是否所有预期事件都存在
    all_events_found = all(event_type in actual_event_types for event_type in expected_event_types)
    
    if all_events_found:
        print("✅ 测试通过：所有预期事件都被成功发布、持久化和查询到")
    else:
        print("❌ 测试失败：部分事件未被查询到")
        
        # 找出缺失的事件类型
        missing_events = [event_type for event_type in expected_event_types if event_type not in actual_event_types]
        print(f"缺失的事件类型: {missing_events}")
    
    print("\n=== 测试完成 ===")
    return all_events_found


if __name__ == "__main__":
    test_event_system()