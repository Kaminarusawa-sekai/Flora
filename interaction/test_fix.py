import json
from external.database.dialog_state_repo import DialogStateRepository
from common.response_state import DialogStateDTO
from datetime import datetime, timezone

# 创建测试数据，模拟旧数据中缺失user_id、name、description字段
old_data = {
    "session_id": "test_session_1",
    "current_intent": "test_intent",
    "is_in_idle_mode": False,
    "requires_clarification": False,
    "waiting_for_confirmation": False,
    "last_updated": datetime.now(timezone.utc).isoformat()
}

# 将测试数据转换为JSON字符串
old_data_json = json.dumps(old_data)

# 创建DialogStateRepository实例
repo = DialogStateRepository()

# 测试反序列化旧数据
print("Testing deserialization of old data...")
try:
    dialog_state = repo._deserialize_state(old_data_json)
    print(f"✅ Deserialization successful!")
    print(f"   Session ID: {dialog_state.session_id}")
    print(f"   User ID: '{dialog_state.user_id}'")
    print(f"   Name: '{dialog_state.name}'")
    print(f"   Description: '{dialog_state.description}'")
    print(f"   Current Intent: {dialog_state.current_intent}")
except Exception as e:
    print(f"❌ Deserialization failed: {e}")

# 测试保存和获取完整流程
print("\nTesting save and get dialog state...")
try:
    # 创建一个完整的DialogStateDTO
    new_state = DialogStateDTO(
        session_id="test_session_2",
        user_id="test_user",
        name="Test Session",
        description="A test session for verification",
        current_intent="test_intent"
    )
    
    # 保存状态
    save_result = repo.save_dialog_state(new_state)
    print(f"✅ Save result: {save_result}")
    
    # 获取状态
    retrieved_state = repo.get_dialog_state("test_session_2")
    if retrieved_state:
        print(f"✅ Retrieved state successfully!")
        print(f"   Session ID: {retrieved_state.session_id}")
        print(f"   User ID: '{retrieved_state.user_id}'")
        print(f"   Name: '{retrieved_state.name}'")
        print(f"   Description: '{retrieved_state.description}'")
        print(f"   Current Intent: {retrieved_state.current_intent}")
    else:
        print(f"❌ Failed to retrieve state")
except Exception as e:
    print(f"❌ Save/get failed: {e}")

print("\nAll tests completed!")
