#!/usr/bin/env python3
"""测试序列化功能"""
import sys
import os
import json
from datetime import datetime, timezone

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from external.database.dialog_state_repo import DialogStateRepository
from common.response_state import DialogStateDTO
from common.task_draft import TaskDraftDTO, TaskDraftStatus, SlotValueDTO, ScheduleDTO
from common.base import SlotSource


def test_serialization():
    """测试序列化功能"""
    print("=== 测试序列化功能 ===")
    
    try:
        # 创建完整的 TaskDraftDTO 对象
        draft = TaskDraftDTO(
            draft_id="test_draft_789",
            task_type="CRAWLER",
            status=TaskDraftStatus.FILLING,
            slots={
                "url": SlotValueDTO(
                    raw="https://example.com",
                    resolved="https://example.com",
                    confirmed=True,
                    source=SlotSource.USER
                ),
                "frequency": SlotValueDTO(
                    raw="每天",
                    resolved="daily",
                    confirmed=False,
                    source=SlotSource.USER
                )
            },
            schedule=ScheduleDTO(
                type="RECURRING",
                natural_language="每天早上8点",
                timezone="Asia/Shanghai"
            ),
            missing_slots=["depth"],
            original_utterances=["帮我爬取example.com", "每天一次"]
        )
        
        # 创建 DialogStateDTO 对象
        dialog_state = DialogStateDTO(
            session_id="test_session_101",
            user_id="user_202",
            current_intent="create_task",
            active_task_draft=draft,
            pending_tasks=["draft_456"]
        )
        
        # 实例化repo
        repo = DialogStateRepository()
        
        # 测试序列化
        serialized = repo._serialize_state(dialog_state)
        print(f"✅ 序列化成功！输出长度: {len(serialized)}")
        
        # 打印部分序列化结果以便查看
        print(f"   前200字符: {serialized[:200]}...")
        
        # 测试反序列化（确保序列化后能正确反序列化回来）
        deserialized = repo._deserialize_state(serialized)
        print("✅ 序列化后反序列化成功！")
        
        # 验证关键字段
        print(f"   原始状态: status={dialog_state.active_task_draft.status}, type={type(dialog_state.active_task_draft.status).__name__}")
        print(f"   反序列化后: status={deserialized.active_task_draft.status}, type={type(deserialized.active_task_draft.status).__name__}")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_serialization_options():
    """测试不同序列化选项的效果"""
    print("\n=== 测试不同序列化选项 ===")
    
    try:
        # 创建测试对象
        draft = TaskDraftDTO(
            draft_id="test_draft_303",
            task_type="CRAWLER",
            status=TaskDraftStatus.FILLING,
            slots={}
        )
        
        dialog_state = DialogStateDTO(
            session_id="test_session_404",
            user_id="user_505",
            active_task_draft=draft
        )
        
        # 测试不同的序列化选项
        from common.response_state import DialogStateDTO
        
        # 默认选项
        default_json = dialog_state.model_dump_json()
        print(f"默认选项: {len(default_json)} 字符")
        
        # 排除 None 值
        exclude_none_json = dialog_state.model_dump_json(exclude_none=True)
        print(f"排除 None 值: {len(exclude_none_json)} 字符")
        
        # 打印对比
        print(f"节省空间: {len(default_json) - len(exclude_none_json)} 字符 ({((len(default_json) - len(exclude_none_json))/len(default_json)*100):.1f}%)")
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    """运行测试"""
    test1_passed = test_serialization()
    test2_passed = test_serialization_options()
    
    if test1_passed and test2_passed:
        print("\n🎉 所有测试通过！序列化功能正常！")
        sys.exit(0)
    else:
        print("\n⚠️  部分测试失败！")
        sys.exit(1)
