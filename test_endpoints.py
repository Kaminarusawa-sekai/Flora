#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简单的API端点测试脚本，用于检查API端点是否能正常响应请求
"""

import sys
import os
import traceback
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """主函数，运行所有端点测试"""
    print("开始测试API端点...\n")
    
    # 导入FastAPI应用
    try:
        from events.main import app
        
        print("✓ 成功导入FastAPI应用")
    except Exception as e:
        print(f"✗ 导入FastAPI应用失败: {traceback.format_exc()}")
        sys.exit(1)
    
    # 创建测试客户端 - 使用lifespan上下文管理器（用于集成测试）
    with TestClient(app) as client:
        # 测试根路径
        test_root_endpoint(client)
        
        # 测试健康检查端点
        test_health_endpoint(client)
        
        # # 测试命令端点
        test_commands_endpoints(client)
        
        # # 测试查询端点
        # test_queries_endpoints(client)
    
    print("\n所有端点测试完成！")


def test_root_endpoint(client):
    """测试根路径端点"""
    print("=== 测试根路径端点 ===")
    response = client.get("/")
    print(f"GET / -> 状态码: {response.status_code}, 响应: {response.json()}")


def test_health_endpoint(client):
    """测试健康检查端点"""
    print("\n=== 测试健康检查端点 ===")
    response = client.get("/health")
    print(f"GET /health -> 状态码: {response.status_code}, 响应: {response.json()}")


def test_commands_endpoints(client):
    """测试命令端点"""
    print("\n=== 测试命令端点 ===")
    
    # 测试启动跟踪端点
    print("\n1. 测试启动跟踪端点")
    try:
        response = client.post("/api/v1/traces/start", json={
            "root_def_id": "DEFAULT_ROOT_AGENT",
            "input_params": {"test": "value"}
        })
        print(f"POST /api/v1/traces/start -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        # 保存trace_id用于后续测试
        trace_id = response.json().get("trace_id", "test_trace")
    except Exception as e:
        print(f"POST /api/v1/traces/start -> 发生错误: {traceback.format_exc()}")
        trace_id = "test_trace"
    
    # 测试取消跟踪端点
    print("\n2. 测试取消跟踪端点")
    try:
        response = client.post(f"/api/v1/traces/{trace_id}/cancel")
        print(f"POST /api/v1/traces/{trace_id}/cancel -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"POST /api/v1/traces/{trace_id}/cancel -> 发生错误: {traceback.format_exc()}")
    
    # 测试暂停跟踪端点
    print("\n3. 测试暂停跟踪端点")
    try:
        response = client.post(f"/api/v1/traces/{trace_id}/pause")
        print(f"POST /api/v1/traces/{trace_id}/pause -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"POST /api/v1/traces/{trace_id}/pause -> 发生错误: {traceback.format_exc()}")
    
    # 测试拆分任务端点
    print("\n4. 测试拆分任务端点")
    try:
        response = client.post(f"/api/v1/traces/{trace_id}/split", json={
            "parent_id": "test_parent",
            "subtasks_meta": [
                {"def_id": "DEFAULT_CHILD_AGENT", "name": "测试子任务1", "params": {"test": "value1"}},
                {"def_id": "DEFAULT_CHILD_AGENT", "name": "测试子任务2", "params": {"test": "value2"}}
            ]
        })
        print(f"POST /api/v1/traces/{trace_id}/split -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        # 保存child_id用于后续测试
        child_ids = response.json().get("child_ids", ["test_child"])
        instance_id = child_ids[0] if child_ids else "test_child"
    except Exception as e:
        print(f"POST /api/v1/traces/{trace_id}/split -> 发生错误: {traceback.format_exc()}")
        instance_id = "test_child"
    
    # 测试恢复跟踪端点
    print("\n5. 测试恢复跟踪端点")
    try:
        response = client.post(f"/api/v1/traces/{trace_id}/resume")
        print(f"POST /api/v1/traces/{trace_id}/resume -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"POST /api/v1/traces/{trace_id}/resume -> 发生错误: {traceback.format_exc()}")
    
    # 测试查询跟踪状态端点
    print("\n6. 测试查询跟踪状态端点")
    try:
        response = client.get(f"/api/v1/traces/{trace_id}/status")
        print(f"GET /api/v1/traces/{trace_id}/status -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"GET /api/v1/traces/{trace_id}/status -> 发生错误: {traceback.format_exc()}")
    
    # 测试级联控制端点（使用新的路由路径）
    print("\n7. 测试级联控制端点")
    try:
        response = client.post(f"/api/v1/traces/{trace_id}/nodes/{instance_id}/control", json={
            "signal": "CANCEL"
        })
        print(f"POST /api/v1/traces/{trace_id}/nodes/{instance_id}/control -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"POST /api/v1/traces/{trace_id}/nodes/{instance_id}/control -> 发生错误: {traceback.format_exc()}")


def test_queries_endpoints(client):
    """测试查询端点"""
    print("\n=== 测试查询端点 ===")
    
    # 测试获取跟踪中的任务列表端点
    print("\n1. 测试获取跟踪中的任务列表端点")
    try:
        response = client.get("/api/v1/traces/test_trace/tasks?status=RUNNING")
        print(f"GET /api/v1/traces/test_trace/tasks -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"GET /api/v1/traces/test_trace/tasks -> 发生错误: {traceback.format_exc()}")
    
    # 测试获取跟踪状态端点
    print("\n2. 测试获取跟踪状态端点")
    try:
        response = client.get("/api/v1/traces/test_trace/status")
        print(f"GET /api/v1/traces/test_trace/status -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"GET /api/v1/traces/test_trace/status -> 发生错误: {traceback.format_exc()}")
    
    # 测试获取任务详情端点
    print("\n3. 测试获取任务详情端点")
    try:
        response = client.get("/api/v1/traces/tasks/test_task")
        print(f"GET /api/v1/traces/tasks/test_task -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"GET /api/v1/traces/tasks/test_task -> 发生错误: {traceback.format_exc()}")
    
    # 测试获取就绪任务列表端点
    print("\n4. 测试获取就绪任务列表端点")
    try:
        response = client.get("/api/v1/traces/ready-tasks")
        print(f"GET /api/v1/traces/ready-tasks -> 状态码: {response.status_code}")
        print(f"响应: {response.json()}")
    except Exception as e:
        print(f"GET /api/v1/traces/ready-tasks -> 发生错误: {traceback.format_exc()}")


if __name__ == "__main__":
    main()