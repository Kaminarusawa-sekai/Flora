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
def test_report_execution_event(task_id, event_type="STARTED", extra_data=None):
    print(f"\n=== 测试 3: 上报任务状态 - {event_type} ===")
    base_data = {
        "task_id": task_id,
        "trace_id": TRACE_ID,
        "event_type": event_type,
        "enriched_context_snapshot": {
            "lifecycle": event_type.lower(),
            "timestamp": datetime.now().isoformat()
        },
        "agent_id": "test-agent-123",
        "worker_id": "test-worker-456",
        "realtime_info": {"step": 1},
    }

    if event_type == "COMPLETED":
        base_data["data"] = extra_data or {"result": "success"}
    elif event_type == "FAILED":
        base_data["error"] = "simulated error"

    response = send_post_request("/traces/events", base_data)
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

    AGENT_CODE_TO_NAME = {
        "rules_system_create_active": "规则与系统构建-新增活动",
        "rules_system_create_active_center": "规则与系统构建-新增活动中心",
        "private_domain": "私域营销",
        "fission_activity": "裂变活动策划",
        "fission_implement": "裂变实施",
        "fission_mech_design": "裂变机制设计",
        "user_strat_fission": "用户分层裂变设计",
        "activity_creative": "活动创意与立项",
        "def_planning": "定义与规划",
        "fission_user_portrait": "裂变用户分层与画像定义",
        "mech_game_design": "机制与玩法设计",
        "rules_system": "规则与系统构建",
        "strat_fission_strat": "分层裂变策略设计",
        "comm_scripts": "定制沟通话术与素材",
        "copy_planning": "文案策划",
        "fission_game_match": "匹配裂变玩法",
        "gameplay_mode": "玩法模式选择",
        "goal_setting": "目标设定",
        "incentive_system": "激励体系设计",
        "strat_incentives": "设计分层激励",
        "strat_portraits": "绘制分层画像",
    }

    TASK_TREE = {
        "private_domain": [
            "user_strat_fission",
            "fission_mech_design",
            "copy_planning",
            "comm_scripts"
        ],
        "user_strat_fission": [
            "strat_portraits",
            "strat_fission_strat"
        ],
        "strat_fission_strat": [
            "fission_game_match",
            "strat_incentives"
        ],
        "fission_mech_design": [
            "goal_setting"
        ],
        "strat_portraits": [],
        "fission_game_match": [],
        "strat_incentives": [],
        "goal_setting": [],
        "copy_planning": [],
        "comm_scripts": []
    }

    agent_to_task_id = {}

    try:
        # === 启动根任务 ===
        root_agent_id = "private_domain"
        start_data = {
            "request_id": REQUEST_ID,
            "trace_id": TRACE_ID,
            "input_params": {"campaign": "春节裂变2026"},
            "user_id": TEST_USER_ID
        }
        resp = send_post_request("/traces/start", start_data)
        root_task_id = resp.json().get("root_task_id") or TRACE_ID
        agent_to_task_id[root_agent_id] = root_task_id

        test_report_execution_event(root_task_id, "STARTED")

        # === 第一轮分裂：根 → Level 1 ===
        level1_agents = TASK_TREE[root_agent_id]
        level1_subtasks = []
        for aid in level1_agents:
            task_id = f"{aid}-{str(uuid.uuid4())[:6]}"
            level1_subtasks.append({
                "id": task_id,
                "name": AGENT_CODE_TO_NAME.get(aid, f"任务-{aid}"),
                "params": {"agent_id": aid},
                "actor_type": "AGENT"
            })
            agent_to_task_id[aid] = task_id

        split1_data = {
            "parent_id": root_task_id,
            "trace_id": TRACE_ID,
            "subtasks_meta": level1_subtasks,
            "reasoning_snapshot": {"reason": "启动一级子任务"}
        }
        send_post_request(f"/traces/{TRACE_ID}/split", split1_data)

        # === 执行 Level 1 并按需分裂 Level 2/3 ===
        for aid in level1_agents:
            task_id = agent_to_task_id[aid]
            task_name = AGENT_CODE_TO_NAME.get(aid, aid)
            print(f"\n--- 执行任务: {task_name} ({aid}) ---")
            test_report_execution_event(task_id, "STARTED")

            children = TASK_TREE.get(aid, [])
            if children:
                test_report_execution_event(task_id, "COMPLETED")

                # 分裂子任务
                child_subtasks = []
                for caid in children:
                    ctask_id = f"{caid}-{str(uuid.uuid4())[:6]}"
                    child_subtasks.append({
                        "id": ctask_id,
                        "name": AGENT_CODE_TO_NAME.get(caid, f"任务-{caid}"),
                        "params": {"agent_id": caid},
                        "actor_type": "AGENT"
                    })
                    agent_to_task_id[caid] = ctask_id

                split_data = {
                    "parent_id": task_id,
                    "trace_id": TRACE_ID,
                    "subtasks_meta": child_subtasks,
                    "reasoning_snapshot": {"reason": f"由 {task_name} 分裂子任务"}
                }
                send_post_request(f"/traces/{TRACE_ID}/split", split_data)

                # 执行子任务（叶子节点）
                for caid in children:
                    ctask_id = agent_to_task_id[caid]
                    cname = AGENT_CODE_TO_NAME.get(caid, caid)
                    print(f"  └─ 执行子任务: {cname}")
                    test_report_execution_event(ctask_id, "STARTED")
                    test_report_execution_event(ctask_id, "COMPLETED")
            else:
                test_report_execution_event(task_id, "COMPLETED")

        # === 根任务完成 ===
        test_report_execution_event(root_task_id, "COMPLETED")

        # === 查询状态 ===
        test_get_trace_status()

        print("\n✅ 多层级逐次分裂 + 真实任务名称 测试完成！")

    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
