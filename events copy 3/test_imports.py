#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的导入测试脚本，用于检查 API 模块的导入路径是否正确
"""

import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_commands_import():
    """测试 commands.py 模块的导入"""
    print("=== 测试 commands.py 导入 ===")
    
    try:
        # 尝试导入 commands.py 中的路由和依赖
        from entry.api.v1.commands import router as commands_router
        from entry.api.deps import get_lifecycle_service, get_signal_service
        from services.lifecycle_service import LifecycleService
        from services.signal_service import SignalService
        
        print("✓ 成功导入 commands.py 中的所有模块")
        print(f"✓ 命令路由: {commands_router}")
        print(f"✓ 生命周期服务依赖: {get_lifecycle_service}")
        print(f"✓ 信号服务依赖: {get_signal_service}")
        print(f"✓ 生命周期服务类: {LifecycleService}")
        print(f"✓ 信号服务类: {SignalService}")
        return True
        
    except ImportError as e:
        print(f"✗ commands.py 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ commands.py 导入时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_queries_import():
    """测试 queries.py 模块的导入"""
    print("\n=== 测试 queries.py 导入 ===")
    
    try:
        # 尝试导入 queries.py 中的路由和依赖
        from entry.api.v1.queries import router as queries_router
        from entry.api.deps import get_observer_service, get_db_session
        from services.observer_service import ObserverService
        from common.task_instance import TaskInstance
        from external.db.base import TaskInstanceRepository
        
        print("✓ 成功导入 queries.py 中的所有模块")
        print(f"✓ 查询路由: {queries_router}")
        print(f"✓ 观察者服务依赖: {get_observer_service}")
        print(f"✓ 数据库会话依赖: {get_db_session}")
        print(f"✓ 观察者服务类: {ObserverService}")
        print(f"✓ 任务实例类: {TaskInstance}")
        print(f"✓ 任务实例仓库类: {TaskInstanceRepository}")
        return True
        
    except ImportError as e:
        print(f"✗ queries.py 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ queries.py 导入时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deps_import():
    """测试 deps.py 模块的导入"""
    print("\n=== 测试 deps.py 导入 ===")
    
    try:
        # 尝试导入 deps.py 中的所有内容
        from entry.api.deps import (
            get_db_session,
            get_lifecycle_service,
            get_signal_service,
            get_observer_service
        )
        
        print("✓ 成功导入 deps.py 中的所有依赖注入函数")
        print(f"✓ 数据库会话: {get_db_session}")
        print(f"✓ 生命周期服务: {get_lifecycle_service}")
        print(f"✓ 信号服务: {get_signal_service}")
        print(f"✓ 观察者服务: {get_observer_service}")
        return True
        
    except ImportError as e:
        print(f"✗ deps.py 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ deps.py 导入时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_v1_init_import():
    """测试 v1/__init__.py 模块的导入"""
    print("\n=== 测试 v1/__init__.py 导入 ===")
    
    try:
        # 尝试导入 v1/__init__.py 中的路由
        from entry.api.v1 import router as v1_router
        
        print("✓ 成功导入 v1/__init__.py 中的路由")
        print(f"✓ v1 路由: {v1_router}")
        return True
        
    except ImportError as e:
        print(f"✗ v1/__init__.py 导入失败: {e}")
        return False
    except Exception as e:
        print(f"✗ v1/__init__.py 导入时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """运行所有导入测试"""
    print("开始测试 API 模块的导入路径...\n")
    
    # 运行所有测试
    results = [
        test_commands_import(),
        test_queries_import(),
        test_deps_import(),
        test_api_v1_init_import()
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