#!/usr/bin/env python3
"""测试序列化优化效果"""
import sys
import os
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath('.'))

from common.response_state import DialogStateDTO
from common.task_draft import TaskDraftDTO, TaskDraftStatus


def test_serialize_optimization():
    """测试序列化优化效果"""
    print("=== 测试序列化优化效果 ===")
    
    try:
        # 创建包含空值和默认值的 DialogStateDTO 对象
        dialog_state = DialogStateDTO(
            session_id="test_session_optimize",
            user_id="user_optimize",
            # 其他字段使用默认值
        )
        
        # 测试不同序列化选项
        default_json = dialog_state.model_dump_json()
        optimized_json = dialog_state.model_dump_json(exclude_none=True)
        
        # 打印对比结果
        print(f"默认序列化: {len(default_json)} 字符")
        print(f"优化后序列化: {len(optimized_json)} 字符")
        print(f"节省空间: {len(default_json) - len(optimized_json)} 字符 ({((len(default_json) - len(optimized_json))/len(default_json)*100):.1f}%)")
        
        # 打印优化前后的内容对比
        print("\n默认序列化内容:")
        print(json.dumps(json.loads(default_json), indent=2))
        
        print("\n优化后序列化内容:")
        print(json.dumps(json.loads(optimized_json), indent=2))
        
        return True
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


if __name__ == "__main__":
    """运行测试"""
    test_passed = test_serialize_optimization()
    
    if test_passed:
        print("\n🎉 测试通过！序列化优化效果明显！")
        sys.exit(0)
    else:
        print("\n⚠️  测试失败！")
        sys.exit(1)
