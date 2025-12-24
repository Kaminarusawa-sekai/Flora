#!/usr/bin/env python3
"""测试 dialog_state_repo.py 的修复"""
import sys
import os
import json
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from external.database.dialog_state_repo import DialogStateRepository
from common.response_state import DialogStateDTO


def test_deserialize_state():
    """测试反序列化方法"""
    print("=== 测试 DialogStateRepository._deserialize_state 修复 ===")
    
    # 创建测试用的旧格式JSON数据（缺少一些新字段）
    old_format_json = json.dumps({
        "session_id": "test_session_123",
        "current_intent": "create_task",
        "pending_tasks": ["draft_456"]
    })
    
    try:
        # 实例化repo
        repo = DialogStateRepository()
        
        # 测试反序列化
        dialog_state = repo._deserialize_state(old_format_json)
        
        print("✅ 反序列化成功！")
        print(f"   session_id: {dialog_state.session_id}")
        print(f"   user_id: {dialog_state.user_id}")
        print(f"   current_intent: {dialog_state.current_intent}")
        print(f"   pending_tasks: {dialog_state.pending_tasks}")
        print(f"   is_in_idle_mode: {dialog_state.is_in_idle_mode}")
        print(f"   waiting_for_confirmation: {dialog_state.waiting_for_confirmation}")
        print(f"   last_updated: {dialog_state.last_updated}")
        
        return True
    except Exception as e:
        print(f"❌ 反序列化失败: {e}")
        return False


def test_complete_state():
    """测试完整状态的序列化和反序列化"""
    print("\n=== 测试完整状态的序列化和反序列化 ===")
    
    try:
        # 创建完整的DialogStateDTO实例
        full_state = DialogStateDTO(
            session_id="test_session_456",
            user_id="user_789",
            current_intent="update_task",
            pending_tasks=["task_123", "task_456"],
            recent_tasks=[],
            is_in_idle_mode=True,
            waiting_for_confirmation=True,
            confirmation_action="delete_task"
        )
        
        # 实例化repo
        repo = DialogStateRepository()
        
        # 序列化
        serialized = repo._serialize_state(full_state)
        print(f"✅ 序列化成功: {serialized[:100]}...")
        
        # 反序列化
        deserialized = repo._deserialize_state(serialized)
        print("✅ 反序列化成功！")
        print(f"   session_id: {deserialized.session_id}")
        print(f"   user_id: {deserialized.user_id}")
        print(f"   is_in_idle_mode: {deserialized.is_in_idle_mode}")
        print(f"   waiting_for_confirmation: {deserialized.waiting_for_confirmation}")
        
        return True
    except Exception as e:
        print(f"❌ 完整状态测试失败: {e}")
        return False


if __name__ == "__main__":
    """运行测试"""
    test1_passed = test_deserialize_state()
    test2_passed = test_complete_state()
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！修复成功！")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败！")
        sys.exit(1)
