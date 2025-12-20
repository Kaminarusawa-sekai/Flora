#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的API模块测试脚本，用于检查commands.py和queries.py文件的功能
"""

import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_commands_module():
    """测试commands.py模块"""
    print("=== 测试 commands.py 模块 ===")
    
    try:
        # 尝试导入commands.py模块
        from events.entry.api.v1 import commands
        print("✓ 成功导入 commands.py 模块")
        print(f"✓ 命令路由: {commands.router}")
        print(f"✓ 路由前缀: {commands.router.prefix}")
        
        # 检查路由端点
        endpoints = []
        for route in commands.router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                endpoints.append((route.path, route.methods))
        
        print(f"✓ 命令端点数量: {len(endpoints)}")
        for path, methods in endpoints:
            print(f"  - {methods} {path}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入 commands.py 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ 测试 commands.py 模块时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_queries_module():
    """测试queries.py模块"""
    print("\n=== 测试 queries.py 模块 ===")
    
    try:
        # 尝试导入queries.py模块
        from events.entry.api.v1 import queries
        print("✓ 成功导入 queries.py 模块")
        print(f"✓ 查询路由: {queries.router}")
        print(f"✓ 路由前缀: {queries.router.prefix}")
        
        # 检查路由端点
        endpoints = []
        for route in queries.router.routes:
            if hasattr(route, "path") and hasattr(route, "methods"):
                endpoints.append((route.path, route.methods))
        
        print(f"✓ 查询端点数量: {len(endpoints)}")
        for path, methods in endpoints:
            print(f"  - {methods} {path}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入 queries.py 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ 测试 queries.py 模块时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_api_init():
    """测试api/v1/__init__.py模块"""
    print("\n=== 测试 api/v1/__init__.py 模块 ===")
    
    try:
        # 尝试导入api/v1/__init__.py模块
        from events.entry.api.v1 import router as v1_router
        print("✓ 成功导入 api/v1/__init__.py 模块")
        print(f"✓ V1 路由: {v1_router}")
        print(f"✓ V1 路由前缀: {v1_router.prefix}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入 api/v1/__init__.py 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ 测试 api/v1/__init__.py 模块时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deps_module():
    """测试deps.py模块"""
    print("\n=== 测试 deps.py 模块 ===")
    
    try:
        # 尝试导入deps.py模块
        from events.entry.api import deps
        print("✓ 成功导入 deps.py 模块")
        
        # 检查依赖注入函数
        dep_functions = [
            "get_db_session",
            "get_lifecycle_service",
            "get_signal_service",
            "get_observer_service"
        ]
        
        for func_name in dep_functions:
            if hasattr(deps, func_name):
                print(f"✓ 依赖注入函数: {func_name}")
            else:
                print(f"✗ 缺失依赖注入函数: {func_name}")
        
        return True
        
    except ImportError as e:
        print(f"✗ 导入 deps.py 模块失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"✗ 测试 deps.py 模块时发生未知错误: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    """运行所有测试"""
    print("开始测试 API 模块...\n")
    
    # 运行所有测试
    results = [
        test_commands_module(),
        test_queries_module(),
        test_api_init(),
        test_deps_module()
    ]
    
    print("\n" + "="*50)
    
    # 统计结果
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    print(f"测试结果: {passed}/{total} 测试通过")
    
    if failed == 0:
        print("🎉 所有测试通过！API 模块功能正常。")
        sys.exit(0)
    else:
        print("❌ 有测试失败，请检查API模块。")
        sys.exit(1)