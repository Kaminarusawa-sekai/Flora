#!/usr/bin/env python3
"""测试 get_sessions_by_user_id 方法"""
import sys
import os
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from external.database.dialog_state_repo import DialogStateRepository
from common.response_state import DialogStateDTO


def test_get_sessions_by_user_id():
    """测试根据用户ID获取会话的方法"""
    print("=== 测试 get_sessions_by_user_id 方法 ===")
    
    try:
        # 实例化repo
        repo = DialogStateRepository()
        
        # 创建测试会话数据
        test_time = datetime.now(timezone.utc)
        
        # 用户1的会话
        session1 = DialogStateDTO(
            session_id="session_1",
            user_id="user_123",
            name="会话1",
            description="用户1的第一个会话",
            current_intent="create_task",
            pending_tasks=[],
            recent_tasks=[],
            is_in_idle_mode=True,
            waiting_for_confirmation=False,
            last_updated=test_time
        )
        
        # 用户1的另一个会话
        session2 = DialogStateDTO(
            session_id="session_2",
            user_id="user_123",
            name="会话2",
            description="用户1的第二个会话",
            current_intent="update_task",
            pending_tasks=[],
            recent_tasks=[],
            is_in_idle_mode=False,
            waiting_for_confirmation=True,
            last_updated=test_time
        )
        
        # 用户2的会话
        session3 = DialogStateDTO(
            session_id="session_3",
            user_id="user_456",
            name="会话3",
            description="用户2的会话",
            current_intent="delete_task",
            pending_tasks=[],
            recent_tasks=[],
            is_in_idle_mode=True,
            waiting_for_confirmation=False,
            last_updated=test_time
        )
        
        # 保存会话
        repo.save_dialog_state(session1)
        repo.save_dialog_state(session2)
        repo.save_dialog_state(session3)
        
        print("✅ 保存测试会话成功！")
        
        # 测试获取用户1的会话
        user1_sessions = repo.get_sessions_by_user_id("user_123")
        print(f"用户user_123的会话: {user1_sessions}")
        print(f"✅ 获取用户user_123的会话成功，共 {len(user1_sessions)} 个会话")
        
        # 验证结果
        expected_session_ids = {"session_1", "session_2"}
        actual_session_ids = {session.session_id for session in user1_sessions}
        
        if actual_session_ids == expected_session_ids:
            print("✅ 用户1的会话ID匹配正确！")
        else:
            print(f"❌ 用户1的会话ID不匹配：期望 {expected_session_ids}，实际 {actual_session_ids}")
            return False
        
        # 测试获取用户2的会话
        user2_sessions = repo.get_sessions_by_user_id("user_456")
        print(f"✅ 获取用户user_456的会话成功，共 {len(user2_sessions)} 个会话")
        
        if len(user2_sessions) == 1 and user2_sessions[0].session_id == "session_3":
            print("✅ 用户2的会话匹配正确！")
        else:
            print(f"❌ 用户2的会话不匹配：期望 session_3，实际 {[s.session_id for s in user2_sessions]}")
            return False
        
        # 测试获取不存在用户的会话
        non_existent_sessions = repo.get_sessions_by_user_id("non_existent_user")
        if len(non_existent_sessions) == 0:
            print("✅ 获取不存在用户的会话返回空列表，正确！")
        else:
            print(f"❌ 获取不存在用户的会话返回了 {len(non_existent_sessions)} 个会话，应该返回0个")
            return False
        
        # 清理测试数据
        repo.delete_dialog_state("session_1")
        repo.delete_dialog_state("session_2")
        repo.delete_dialog_state("session_3")
        
        print("✅ 清理测试数据成功！")
        print("🎉 所有测试通过！get_sessions_by_user_id 方法实现正确！")
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """运行测试"""
    success = test_get_sessions_by_user_id()
    sys.exit(0 if success else 1)
