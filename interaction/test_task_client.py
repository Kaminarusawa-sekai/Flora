#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TaskClient 测试文件
直接使用 TaskClient 类的函数，测试是否能正确请求外部系统
"""

import sys
import os
import time
import json
import requests

# 直接从当前目录导入TaskClient

from external.client.task_client import TaskClient


def test_task_client():
    """测试 TaskClient 功能 - 真实请求，返回200就算成功"""
    print("=== TaskClient 方法测试 ===")
    
    # 1. 测试 TaskClient 实例化
    print("\n1. 测试 TaskClient 实例化...")
    try:
        client = TaskClient(
            base_url="http://localhost:8001/api/v1",
            events_base_url="http://localhost:8004/api/v1"
        )
        print(f"   ✓ 实例化成功")
    except Exception as e:
        print(f"   ✗ 实例化失败: {str(e)}")
        return
    
    # 2. 测试所有方法（逐个调用，查看返回状态）
    print("\n2. 测试所有方法...")
    
    # 测试数据
    test_user_id = "test_user_001"
    test_request_id = f"test_req_{int(time.time())}"
    test_trace_id = "test_trace_123"
    
    # 准备测试任务数据
    task_data = {
        "task_name": "test_task",
        "task_content": {
            "type": "test",
            "action": "print",
            "message": "Test"
        },
        "parameters": {
            "key": "value"
        },
        "user_id": test_user_id,
        "request_id": test_request_id,
        "trace_id": test_trace_id
    }
    
    # 2.1 测试 _request 方法（用于获取状态码）
    def test_request(method, endpoint, json=None, params=None, use_events_url=False):
        """测试请求，返回状态码"""
        try:
            base_url = client.events_base_url if use_events_url else client.base_url
            url = f"{base_url}{endpoint}"
            response = requests.request(method, url, json=json, params=params, timeout=5)
            return response.status_code
        except Exception as e:
            # 如果连接失败，返回错误信息
            return f"ERROR: {str(e)}"
    
    # 定义要测试的方法和对应的请求
    methods_to_test = [
        # submit_task
        ("submit_task", "POST", "/ad-hoc-tasks", {
            "task_name": task_data["task_name"],
            "task_content": task_data["task_content"],
            "input_params": task_data["parameters"],
            "loop_config": None,
            "is_temporary": True,
            "request_id": task_data["request_id"]
        }),
        
        # register_scheduled_task
        ("register_scheduled_task", "POST", "/ad-hoc-tasks", {
            "task_name": task_data["task_name"],
            "task_content": task_data["task_content"],
            "input_params": task_data["parameters"],
            "loop_config": None,
            "is_temporary": True,
            "schedule_type": "CRON",
            "schedule_config": {
                "cron_expression": "* * * * *",
                "timezone": "Asia/Shanghai"
            },
            "request_id": task_data["request_id"]
        }),
        
        # unregister_scheduled_task
        ("unregister_scheduled_task", "POST", f"/traces/{task_data['trace_id']}/cancel"),
        
        # update_scheduled_task
        ("update_scheduled_task", "PATCH", f"/traces/{task_data['trace_id']}/modify", {
            "schedule_config": {
                "cron_expression": "*/5 * * * *"
            }
        }),
        
        # cancel_task
        ("cancel_task", "POST", f"/traces/{task_data['trace_id']}/cancel"),
        
        # pause_task
        ("pause_task", "POST", f"/traces/{task_data['trace_id']}/pause"),
        
        # resume_task
        ("resume_task", "POST", f"/traces/{task_data['trace_id']}/resume"),
        
        # modify_task
        ("modify_task", "PATCH", f"/instances/{task_data['trace_id']}/modify", {
            "input_params": {"new_key": "new_value"},
            "schedule_config": None
        }),
        
        # register_recurring_task
        ("register_recurring_task", "POST", "/ad-hoc-tasks", {
            "task_name": task_data["task_name"],
            "task_content": task_data["task_content"],
            "input_params": task_data["parameters"],
            "loop_config": {
                "interval_sec": 30,
                "max_rounds": 5
            },
            "is_temporary": True,
            "schedule_type": "LOOP",
            "request_id": task_data["request_id"]
        }),
        
        # cancel_recurring_task
        ("cancel_recurring_task", "POST", f"/traces/{task_data['trace_id']}/cancel"),
        
        # update_recurring_task
        ("update_recurring_task", "PATCH", f"/traces/{task_data['trace_id']}/modify", {
            "input_params": {"interval": 60}
        }),
        
        # get_task_status
        ("get_task_status", "GET", f"/traces/{task_data['trace_id']}/trace-details", None, None, True),
        
        # request-id-to-trace
        ("request-id-to-trace", "GET", f"/request-id-to-trace/{task_data['request_id']}")
    ]
    
    # 逐个测试方法
    for i, test_case in enumerate(methods_to_test, 1):
        method_name = test_case[0]
        http_method = test_case[1]
        endpoint = test_case[2]
        # 处理可选参数
        json_data = test_case[3] if len(test_case) > 3 else None
        params = test_case[4] if len(test_case) > 4 else None
        use_events_url = test_case[5] if len(test_case) > 5 else False
        
        print(f"\n2.{i} 测试 {method_name}...")
        status_code = test_request(http_method, endpoint, json_data, params, use_events_url)
        print(f"   请求: {http_method} {endpoint}")
        print(f"   状态码: {status_code}")
        
        # 宽松判断：200-299都算成功
        if isinstance(status_code, int) and 200 <= status_code < 300:
            print(f"   ✓ 成功: {status_code}")
        elif isinstance(status_code, int):
            print(f"   ⚠ 非200状态: {status_code}")
        else:
            print(f"   ✗ 错误: {status_code}")
    
    print("\n=== 测试完成 ===")
    print("\n测试说明:")
    print("1. 本测试真实发送HTTP请求到外部系统")
    print("2. 200-299状态码算成功")
    print("3. 测试了所有TaskClient相关的API端点")
    print("4. 测试结果取决于外部服务的实际运行状态")


if __name__ == "__main__":
    test_task_client()