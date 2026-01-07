import uuid
import json
import requests
from datetime import datetime

# API 基础 URL
BASE_URL = "http://localhost:8004"  # 请根据实际情况修改
API_V1_PREFIX = f"{BASE_URL}/api/v1"

# 测试用的 request_id
REQUEST_ID = "c27d2e14-76ff-4284-b977-052aa965bc64"

# 生成 trace_id
TRACE_ID = f"test-trace-{str(uuid.uuid4())[:8]}"

# 测试数据
TEST_USER_ID = "test-user-123"

# 辅助函数：发送 POST 请求
def send_post_request(endpoint, data):
    url = f"{API_V1_PREFIX}{endpoint}"
    headers = {
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=data, headers=headers)
    print(f"\nPOST {endpoint}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response

# 辅助函数：发送 GET 请求
def send_get_request(endpoint):
    url = f"{API_V1_PREFIX}{endpoint}"
    response = requests.get(url)
    print(f"\nGET {endpoint}")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response

# 测试 1：启动 trace (创建根节点)
def test_start_trace():
    print("=== 测试 1: 启动 Trace ===")
    data = {
        "request_id": REQUEST_ID,
        "trace_id": TRACE_ID,
        "input_params": {"test_param": "test_value"},
        "user_id": TEST_USER_ID
    }
    response = send_post_request("/traces/start", data)
    return response.json().get("trace_id")

# 测试 2：分裂任务 (测试 split_task)
def test_split_task(trace_id, parent_id):
    print("\n=== 测试 2: 分裂任务 ===")
    subtasks_meta = [
        {
            "id": f"subtask-{str(uuid.uuid4())[:8]}",
            "name": "Subtask 1",
            "params": {"subtask_param": "value1"},
            "actor_type": "AGENT"
        },
        {
            "id": f"subtask-{str(uuid.uuid4())[:8]}",
            "name": "Subtask 2",
            "params": {"subtask_param": "value2"},
            "actor_type": "AGENT"
        }
    ]
    
    data = {
        "parent_id": parent_id,
        "trace_id": trace_id,
        "subtasks_meta": subtasks_meta,
        "reasoning_snapshot": {"reason": "Test split task"}
    }
    
    response = send_post_request(f"/traces/{trace_id}/split", data)
    return response.json().get("new_child_ids", [])

# 测试 3：上报任务状态 (测试 report_execution_event)
def test_report_execution_event(task_id, event_type="STARTED"):
    print(f"\n=== 测试 3: 上报任务状态 - {event_type} ===")
    data = {
        "task_id": task_id,
        "trace_id": TRACE_ID,
        "event_type": event_type,
        "enriched_context_snapshot": {
            "lifecycle": event_type.lower(),
            "timestamp": datetime.now().isoformat()
        },
        "data": {"result": "test_result"} if event_type == "COMPLETED" else None,
        "error": "test error" if event_type == "FAILED" else None,
        "agent_id": "test-agent-123",
        "worker_id": "test-worker-456",
        "realtime_info": {"step": 1}
    }
    
    response = send_post_request("/traces/events", data)
    return response.json()

# 测试 4：查询 trace 状态
def test_get_trace_status():
    print("\n=== 测试 4: 查询 Trace 状态 ===")
    response = send_get_request(f"/traces/{TRACE_ID}/status")
    return response.json()

# 主测试函数
def main():
    print(f"开始测试 API 端点，使用 request_id: {REQUEST_ID}")
    print(f"Generated trace_id: {TRACE_ID}")
    
    try:
        # 1. 启动 trace
        trace_id = test_start_trace()
        if not trace_id:
            print("\n❌ 启动 Trace 失败，无法继续测试")
            return
        
        # 2. 假设根节点 ID 是 trace_id 的一部分（或者根据实际情况获取）
        # 这里简化处理，直接使用 trace_id 作为根节点 ID
        root_task_id = trace_id
        
        # 3. 测试上报根节点开始状态
        test_report_execution_event(root_task_id, "STARTED")
        
        # 4. 测试分裂任务
        child_ids = test_split_task(trace_id, root_task_id)
        if not child_ids:
            print("\n❌ 分裂任务失败，无法继续测试")
            return
        
        # 5. 测试上报子节点状态
        for child_id in child_ids:
            test_report_execution_event(child_id, "STARTED")
            test_report_execution_event(child_id, "COMPLETED")
        
        # 6. 测试上报根节点完成状态
        test_report_execution_event(root_task_id, "COMPLETED")
        
        # 7. 测试查询 trace 状态
        test_get_trace_status()
        
        print("\n✅ 所有测试完成！")
        
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
