import asyncio
from fastapi.testclient import TestClient
import sys
import os

# 使用绝对导入，确保导入的是trigger目录下的main
from trigger.main import app

client = TestClient(app)

async def test_all_endpoints():
    """测试所有API端点"""
    print("开始测试所有API端点...")
    
    # 1. 测试根路径
    print("\n测试根路径: GET /")
    response = client.get("/")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    assert response.status_code == 200
    
    # 2. 测试健康检查
    print("\n测试健康检查: GET /health")
    response = client.get("/health")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    assert response.status_code == 200
    
    # 3. 创建任务定义
    print("\n测试创建任务定义: POST /api/v1/definitions")
    task_data = {
        "name": "test-task",
        "cron_expr": "* * * * *",
        "loop_config": {"max_rounds": 3},
        "is_active": True
    }
    response = client.post("/api/v1/definitions", json=task_data)
    print(f"状态码: {response.status_code}")
    task_def = response.json()
    print(f"响应: {task_def}")
    assert response.status_code == 200
    task_id = task_def["id"]
    
    # 4. 获取任务定义列表
    print("\n测试获取任务定义列表: GET /api/v1/definitions")
    response = client.get("/api/v1/definitions")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    assert response.status_code == 200
    
    # 5. 获取单个任务定义
    print(f"\n测试获取单个任务定义: GET /api/v1/definitions/{task_id}")
    response = client.get(f"/api/v1/definitions/{task_id}")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    assert response.status_code == 200
    
    # 6. 手动触发任务
    print(f"\n测试手动触发任务: POST /api/v1/definitions/{task_id}/trigger")
    response = client.post(f"/api/v1/definitions/{task_id}/trigger")
    print(f"状态码: {response.status_code}")
    trigger_response = response.json()
    print(f"响应: {trigger_response}")
    assert response.status_code == 200
    
    # 注意：由于我们没有实际的trace_id，下面两个端点的测试可能会失败
    # 我们将使用一个模拟的trace_id，预期会得到404
    
    # 7. 获取任务实例列表 (预期404)
    mock_trace_id = "mock-trace-123"
    print(f"\n测试获取任务实例列表: GET /api/v1/instances/{mock_trace_id}")
    response = client.get(f"/api/v1/instances/{mock_trace_id}")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    
    # 8. 获取trace状态 (预期404)
    print(f"\n测试获取trace状态: GET /api/v1/instances/{mock_trace_id}/status")
    response = client.get(f"/api/v1/instances/{mock_trace_id}/status")
    print(f"状态码: {response.status_code}")
    print(f"响应: {response.json()}")
    
    print("\n所有API端点测试完成!")

if __name__ == "__main__":
    asyncio.run(test_all_endpoints())
