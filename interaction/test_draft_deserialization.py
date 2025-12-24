#!/usr/bin/env python3
"""测试 TaskDraftDTO 反序列化修复"""
import sys
import os
import json
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from external.database.dialog_state_repo import DialogStateRepository
from common.response_state import DialogStateDTO
from common.task_draft import TaskDraftDTO, TaskDraftStatus


def test_draft_with_enums():
    """测试包含枚举值的 TaskDraft 反序列化"""
    print("=== 测试包含枚举值的 TaskDraft 反序列化 ===")
    
    # 创建包含枚举值的测试JSON数据
    test_json = json.dumps({
        "session_id": "test_session_789",
        "user_id": "user_123",
        "current_intent": "create_task",
        "active_task_draft": {
            "draft_id": "test_draft_123",
            "task_type": "CRAWLER",
            "status": "FILLING",
            "slots": {
                "url": {
                    "raw": "https://example.com",
                    "resolved": "https://example.com",
                    "confirmed": True,
                    "source": "USER"
                },
                "frequency": {
                    "raw": "每天",
                    "resolved": "daily",
                    "confirmed": False,
                    "source": "USER"
                }
            },
            "schedule": {
                "type": "RECURRING",
                "natural_language": "每天早上8点",
                "timezone": "Asia/Shanghai"
            },
            "missing_slots": ["depth"],
            "original_utterances": ["帮我爬取example.com", "每天一次"]
        },
        "is_in_idle_mode": False
    })
    
    try:
        # 实例化repo
        repo = DialogStateRepository()
        
        # 测试反序列化
        dialog_state = repo._deserialize_state(test_json)
        
        print("✅ 反序列化成功！")
        print(f"   session_id: {dialog_state.session_id}")
        print(f"   user_id: {dialog_state.user_id}")
        print(f"   is_in_idle_mode: {dialog_state.is_in_idle_mode}")
        
        # 检查 active_task_draft
        if dialog_state.active_task_draft:
            print(f"   draft_id: {dialog_state.active_task_draft.draft_id}")
            print(f"   task_type: {dialog_state.active_task_draft.task_type}")
            print(f"   status: {dialog_state.active_task_draft.status} (类型: {type(dialog_state.active_task_draft.status).__name__})")
            print(f"   slots: {list(dialog_state.active_task_draft.slots.keys())}")
            
            # 检查 slots 中的枚举值
            for slot_name, slot_value in dialog_state.active_task_draft.slots.items():
                print(f"     - {slot_name}: source={slot_value.source} (类型: {type(slot_value.source).__name__})")
            
            # 检查 schedule
            if dialog_state.active_task_draft.schedule:
                print(f"   schedule: type={dialog_state.active_task_draft.schedule.type}")
            
            # 检查其他字段
            print(f"   is_dynamic_schema: {dialog_state.active_task_draft.is_dynamic_schema}")
            print(f"   completeness_score: {dialog_state.active_task_draft.completeness_score}")
        
        return True
    except Exception as e:
        print(f"❌ 反序列化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """运行测试"""
    test_passed = test_draft_with_enums()
    
    if test_passed:
        print("\n🎉 测试通过！修复成功！")
        sys.exit(0)
    else:
        print("\n⚠️  测试失败！")
        sys.exit(1)
