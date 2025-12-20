#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的导入测试脚本，用于检查 events 服务模块的导入路径是否正确
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))


def test_events_services_import():
    """测试 events services 模块的导入"""
    print("=== 测试 events services 导入 ===")
    try:
        # 尝试导入 events services 中的所有模块
        from events.services.lifecycle_service import LifecycleService
        from events.services.signal_service import SignalService
        from events.services.observer_service import ObserverService
        
        print("✓ 成功导入所有 events services 模块")
        print(f"✓ 生命周期服务类: {LifecycleService}")
        print(f"✓ 信号服务类: {SignalService}")
        print(f"✓ 观察者服务类: {ObserverService}")
        return True
        
    except ImportError as e:
        print(f"✗ events services 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ events services 导入时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_events_common_import():
    """测试 events common 模块的导入"""
    print("\n=== 测试 events common 导入 ===")
    try:
        # 尝试导入 events common 中的模块
        from events.common.event_instance import EventInstance
        from events.common.enums import EventInstanceStatus
        from events.common.event_definition import EventDefinition
        
        print("✓ 成功导入 events common 模块")
        print(f"✓ 事件实例类: {EventInstance}")
        print(f"✓ 事件实例状态枚举: {EventInstanceStatus}")
        print(f"✓ 事件定义类: {EventDefinition}")
        return True
        
    except ImportError as e:
        print(f"✗ events common 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ events common 导入时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """运行所有导入测试"""
    print("开始测试 events 模块的导入路径...\n")
    
    # 运行所有测试
    results = [
        test_events_services_import(),
        test_events_common_import()
    ]
    
    print("\n" + "="*50)
    
    # 统计结果
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"测试结果: {passed}/{total} 测试通过")
    
    if failed == 0:
        print("🎉 所有导入测试通过！导入路径正确。")
        sys.exit(0)
    else:
        print("❌ 有导入测试失败，请检查导入路径。")
        sys.exit(1)
